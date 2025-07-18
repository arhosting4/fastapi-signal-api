import traceback
import httpx
import pandas as pd
import pandas_ta as ta

from strategybot import generate_core_signal, calculate_tp_sl
from patternai import detect_patterns
from riskguardian import check_risk
from sentinel import check_news
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from signal_tracker import add_active_signal

# --- اہم تبدیلی: utils.py سے امپورٹ کریں ---
from utils import fetch_twelve_data_ohlc

def get_higher_timeframe_trend(candles: list) -> str:
    if len(candles) < 50:
        return "neutral"
    df = pd.DataFrame(candles)
    df['close'] = pd.to_numeric(df['close'])
    sma_fast = ta.sma(df['close'], length=20)
    sma_slow = ta.sma(df['close'], length=50)
    if sma_fast is None or sma_slow is None or sma_fast.empty or sma_slow.empty:
        return "neutral"
    if sma_fast.iloc[-1] > sma_slow.iloc[-1]:
        return "up"
    elif sma_fast.iloc[-1] < sma_slow.iloc[-1]:
        return "down"
    else:
        return "neutral"

async def generate_final_signal(symbol: str, candles: list, timeframe: str):
    try:
        core_signal_data = generate_core_signal(symbol, timeframe, candles)
        core_signal = core_signal_data["signal"]
        
        if core_signal == "wait":
            return {"signal": "wait", "reason": "Primary indicators suggest no clear opportunity.", "confidence": 40.0, "tier": "Tier 5 – Weak", "price": candles[-1]['close'], "tp": None, "sl": None, "candles": candles}

        higher_timeframe_map = {"1m": "5m", "5m": "15m", "15m": "1h"}
        confirmation_tf = higher_timeframe_map.get(timeframe)
        
        htf_trend = "neutral"
        if confirmation_tf:
            print(f"CONFIRMATION: Fetching {confirmation_tf} data...")
            htf_candles = await fetch_twelve_data_ohlc(symbol, confirmation_tf)
            if htf_candles:
                htf_trend = get_higher_timeframe_trend(htf_candles)
                print(f"CONFIRMATION: Trend on {confirmation_tf} is '{htf_trend}'.")
            else:
                print(f"Warning: Could not get data for {confirmation_tf}.")

        if (core_signal == "buy" and htf_trend == "down") or \
           (core_signal == "sell" and htf_trend == "up"):
            reason = f"Signal ({core_signal.upper()}) on {timeframe} was blocked by opposing trend on {confirmation_tf}."
            print(f"BLOCK: {reason}")
            return {"signal": "wait", "reason": reason, "confidence": 20.0, "tier": "Tier 5 – Weak", "price": candles[-1]['close'], "tp": None, "sl": None, "candles": candles}

        pattern_data = detect_patterns(candles)
        risk_assessment = check_risk(candles)
        
        async with httpx.AsyncClient() as client:
            news_data = await check_news(symbol, client)

        confidence = get_confidence(core_signal, pattern_data.get("type"), risk_assessment.get("status"), news_data["impact"], symbol)
        
        if (core_signal == "buy" and htf_trend == "up") or \
           (core_signal == "sell" and htf_trend == "down"):
            print("CONFIRMATION: Boosting confidence due to HTF alignment.")
            confidence = min(100.0, confidence + 10)

        tier = get_tier(confidence)
        reason = generate_reason(core_signal, pattern_data, risk_assessment.get("status"), news_data["impact"], confidence)
        
        tp_sl_buy, tp_sl_sell = calculate_tp_sl(candles)
        tp, sl = (tp_sl_buy if core_signal == "buy" else tp_sl_sell) if (tp_sl_buy and tp_sl_sell) else (None, None)

        final_result = {"signal": core_signal, "reason": reason, "confidence": round(confidence, 2), "tier": tier, "price": candles[-1]['close'], "tp": round(tp, 5) if tp is not None else None, "sl": round(sl, 5) if sl is not None else None, "candles": candles}

        if final_result["signal"] in ["buy", "sell"] and tp is not None and sl is not None:
            add_active_signal(final_result)

        return final_result

    except Exception as e:
        traceback.print_exc()
        raise Exception(f"Error in AI fusion for {symbol}: {e}")
            
