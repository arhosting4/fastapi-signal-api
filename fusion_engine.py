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
from signal_tracker import add_active_signal # یہ TP/SL کی نگرانی کے لیے اب بھی استعمال ہوگا

# utils.py سے امپورٹ کریں
from utils import fetch_twelve_data_ohlc

def get_higher_timeframe_trend(candles: list) -> str:
    if len(candles) < 50: return "neutral"
    df = pd.DataFrame(candles)
    df['close'] = pd.to_numeric(df['close'])
    sma_fast = ta.sma(df['close'], length=20)
    sma_slow = ta.sma(df['close'], length=50)
    if sma_fast is None or sma_slow is None: return "neutral"
    if sma_fast.iloc[-1] > sma_slow.iloc[-1]: return "up"
    elif sma_fast.iloc[-1] < sma_slow.iloc[-1]: return "down"
    else: return "neutral"

# --- اہم تبدیلی: ایک نیا پیرامیٹر 'should_save_active' شامل کریں ---
async def generate_final_signal(symbol: str, candles: list, timeframe: str, should_save_active: bool = True):
    """
    یہ مرکزی AI انجن ہے۔ اب یہ کنٹرول کر سکتا ہے کہ سگنل کو فعال ٹریکر میں شامل کرنا ہے یا نہیں۔
    """
    try:
        core_signal_data = generate_core_signal(symbol, timeframe, candles)
        core_signal = core_signal_data["signal"]
        
        if core_signal == "wait":
            return {"signal": "wait", "reason": "Primary indicators suggest no clear opportunity."}

        higher_timeframe_map = {"1m": "5m", "5m": "15m", "15m": "1h"}
        confirmation_tf = higher_timeframe_map.get(timeframe)
        
        htf_trend = "neutral"
        if confirmation_tf:
            htf_candles = await fetch_twelve_data_ohlc(symbol, confirmation_tf)
            if htf_candles: htf_trend = get_higher_timeframe_trend(htf_candles)

        if (core_signal == "buy" and htf_trend == "down") or (core_signal == "sell" and htf_trend == "up"):
            return {"signal": "wait", "reason": f"Signal blocked by opposing trend on {confirmation_tf}."}

        pattern_data = detect_patterns(candles)
        risk_assessment = check_risk(candles)
        
        async with httpx.AsyncClient() as client:
            news_data = await check_news(symbol, client)

        confidence = get_confidence(core_signal, pattern_data.get("type"), risk_assessment.get("status"), news_data["impact"], symbol)
        
        if (core_signal == "buy" and htf_trend == "up") or (core_signal == "sell" and htf_trend == "down"):
            confidence = min(100.0, confidence + 10)

        tier = get_tier(confidence)
        reason = generate_reason(core_signal, pattern_data, risk_assessment.get("status"), news_data["impact"], confidence)
        
        tp_sl_buy, tp_sl_sell = calculate_tp_sl(candles)
        tp, sl = (tp_sl_buy if core_signal == "buy" else tp_sl_sell) if (tp_sl_buy and tp_sl_sell) else (None, None)

        final_result = {
            "symbol": symbol, "timeframe": timeframe, "signal": core_signal, 
            "reason": reason, "confidence": round(confidence, 2), "tier": tier, 
            "price": candles[-1]['close'], "tp": tp, "sl": sl, "candles": candles
        }

        # --- اہم تبدیلی: صرف تب محفوظ کریں جب کہا جائے ---
        if should_save_active and final_result["signal"] in ["buy", "sell"] and tp is not None and sl is not None:
            add_active_signal(final_result)

        return final_result

    except Exception as e:
        traceback.print_exc()
        return {"signal": "wait", "reason": f"An error occurred during analysis: {e}"}
    
