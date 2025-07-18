import traceback
import httpx
import pandas as pd
import pandas_ta as ta

# ہمارے پروجیکٹ کے ایجنٹس
from strategybot import generate_core_signal, calculate_tp_sl
from patternai import detect_patterns
from riskguardian import check_risk
from sentinel import check_news
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from signal_tracker import add_active_signal

# --- نیا فنکشن: بڑے ٹائم فریم کے رجحان کی تصدیق کے لیے ---
def get_higher_timeframe_trend(candles: list) -> str:
    """
    ایک سادہ موونگ ایوریج کراس اوور کا استعمال کرکے بڑے ٹائم فریم کے رجحان کی سمت کا تعین کرتا ہے۔
    """
    if len(candles) < 50: # 50-پیریڈ SMA کے لیے کافی ڈیٹا چاہیے
        return "neutral"

    df = pd.DataFrame(candles)
    df['close'] = pd.to_numeric(df['close'])

    # دو موونگ ایوریجز کا حساب لگائیں
    sma_fast = ta.sma(df['close'], length=20)
    sma_slow = ta.sma(df['close'], length=50)

    if sma_fast is None or sma_slow is None or sma_fast.empty or sma_slow.empty:
        return "neutral"

    # آخری دو کینڈلز کی بنیاد پر رجحان کا تعین کریں
    if sma_fast.iloc[-1] > sma_slow.iloc[-1] and sma_fast.iloc[-2] <= sma_slow.iloc[-2]:
        return "up_momentum" # ابھی ابھی مثبت کراس اوور ہوا
    elif sma_fast.iloc[-1] > sma_slow.iloc[-1]:
        return "up" # پہلے سے ہی اپ ٹرینڈ میں ہے
    elif sma_fast.iloc[-1] < sma_slow.iloc[-1] and sma_fast.iloc[-2] >= sma_slow.iloc[-2]:
        return "down_momentum" # ابھی ابھی منفی کراس اوور ہوا
    elif sma_fast.iloc[-1] < sma_slow.iloc[-1]:
        return "down" # پہلے سے ہی ڈاؤن ٹرینڈ میں ہے
    else:
        return "neutral"

# --- اہم تبدیلی: app.py سے fetch_twelve_data_ohlc کو یہاں امپورٹ کریں ---
# چونکہ fusion_engine کو خود ڈیٹا لانے کی ضرورت ہے، ہمیں یہ فنکشن یہاں چاہیے
# نوٹ: یہ سرکلر امپورٹ سے بچنے کا ایک طریقہ ہے
from app import fetch_twelve_data_ohlc


async def generate_final_signal(symbol: str, candles: list, timeframe: str):
    """
    یہ مرکزی AI انجن ہے جو تمام ایجنٹس سے مل کر حتمی سگنل بناتا ہے۔
    اب اس میں ملٹی ٹائم فریم تصدیق شامل ہے۔
    """
    try:
        # 1. بنیادی ٹائم فریم پر تجزیہ
        core_signal_data = generate_core_signal(symbol, timeframe, candles)
        core_signal = core_signal_data["signal"]
        
        if core_signal == "wait":
            return {
                "signal": "wait", "reason": "Primary indicators suggest no clear opportunity.",
                "confidence": 40.0, "tier": "Tier 5 – Weak", "price": candles[-1]['close'],
                "tp": None, "sl": None, "candles": candles
            }

        # --- 2. ملٹی ٹائم فریم تصدیق ---
        higher_timeframe_map = {"1m": "5m", "5m": "15m", "15m": "1h"}
        confirmation_tf = higher_timeframe_map.get(timeframe)
        
        htf_trend = "neutral"
        if confirmation_tf:
            print(f"CONFIRMATION: Fetching {confirmation_tf} data to confirm {timeframe} signal...")
            try:
                # بڑے ٹائم فریم کا ڈیٹا حاصل کریں
                htf_candles = await fetch_twelve_data_ohlc(symbol, confirmation_tf)
                htf_trend = get_higher_timeframe_trend(htf_candles)
                print(f"CONFIRMATION: Higher timeframe ({confirmation_tf}) trend is '{htf_trend}'.")
            except Exception as e:
                print(f"Warning: Could not get higher timeframe confirmation. Error: {e}")
                htf_trend = "neutral" # اگر کوئی مسئلہ ہو تو غیر جانبدار رہیں

        # اگر بنیادی سگنل اور بڑا رجحان مخالف ہوں تو سگنل کو بلاک کر دیں
        if (core_signal == "buy" and htf_trend in ["down", "down_momentum"]) or \
           (core_signal == "sell" and htf_trend in ["up", "up_momentum"]):
            
            reason = f"Signal ({core_signal.upper()}) on {timeframe} was blocked by opposing trend on {confirmation_tf} timeframe."
            print(f"BLOCK: {reason}")
            return {
                "signal": "wait", "reason": reason, "confidence": 20.0,
                "tier": "Tier 5 – Weak", "price": candles[-1]['close'],
                "tp": None, "sl": None, "candles": candles
            }

        # 3. باقی تجزیہ جاری رکھیں اگر سگنل بلاک نہیں ہوا
        pattern_data = detect_patterns(candles)
        risk_assessment = check_risk(candles)
        
        # (باقی تمام منطق جیسے نیوز، اعتماد، وغیرہ ویسی ہی رہے گی)
        async with httpx.AsyncClient() as client:
            news_data = await check_news(symbol, client)

        confidence = get_confidence(core_signal, pattern_data.get("type"), risk_assessment.get("status"), news_data["impact"], symbol)
        
        # اگر بڑا رجحان بھی ساتھ دے رہا ہو تو اعتماد میں اضافہ کریں
        if (core_signal == "buy" and htf_trend in ["up", "up_momentum"]) or \
           (core_signal == "sell" and htf_trend in ["down", "down_momentum"]):
            print("CONFIRMATION: Boosting confidence due to alignment with higher timeframe.")
            confidence = min(100.0, confidence + 10) # 10 پوائنٹس کا اضافہ

        tier = get_tier(confidence)
        reason = generate_reason(core_signal, pattern_data, risk_assessment.get("status"), news_data["impact"], confidence)
        
        tp_sl_buy, tp_sl_sell = calculate_tp_sl(candles)
        tp, sl = (tp_sl_buy if core_signal == "buy" else tp_sl_sell) if (tp_sl_buy and tp_sl_sell) else (None, None)

        final_result = {
            "signal": core_signal, "reason": reason, "confidence": round(confidence, 2),
            "tier": tier, "price": candles[-1]['close'],
            "tp": round(tp, 5) if tp is not None else None,
            "sl": round(sl, 5) if sl is not None else None,
            "candles": candles
        }

        if final_result["signal"] in ["buy", "sell"] and tp is not None and sl is not None:
            add_active_signal(final_result)

        return final_result

    except Exception as e:
        print(f"CRITICAL ERROR in fusion_engine for {symbol}: {e}")
        traceback.print_exc()
        raise Exception(f"Error in AI fusion for {symbol}: {e}")
        
