from strategybot import generate_core_signal, calculate_tp_sl
from patternai import detect_patterns
from riskguardian import check_risk
from sentinel import check_news
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from signal_tracker import add_active_signal
import traceback

# اہم: fusion_engine کو بھی async بنائیں
async def generate_final_signal(symbol: str, candles: list, timeframe: str):
    """
    Core AI fusion engine combining all agents to generate a god-level trading signal.
    """
    try:
        closes = [float(c["close"]) for c in candles]
        highs = [float(c["high"]) for c in candles]
        lows = [float(c["low"]) for c in candles]

        core_signal = generate_core_signal(symbol, timeframe, closes)
        
        if core_signal == "wait" and len(closes) < 34:
            return {
                "status": "no-signal", "symbol": symbol, "signal": "wait",
                "reason": "Insufficient historical data.", "confidence": 50.0,
                "tier": "Tier 5 – Weak", "timeframe": timeframe, "price": closes[-1],
                "tp": None, "sl": None, "candles": candles
            }

        pattern_data = detect_patterns(candles)
        risk_assessment = check_risk(candles)
        risk_status = risk_assessment.get("status", "Normal")
        risk_reason = risk_assessment.get("reason", "Market risk appears normal.")

        if risk_status == "High":
            return {
                "status": "blocked", "symbol": symbol, "signal": "wait",
                "reason": f"Trading BLOCKED: {risk_reason}", "confidence": 0.0,
                "tier": "Tier 5 – Weak", "timeframe": timeframe, "price": closes[-1],
                "tp": None, "sl": None, "candles": candles
            }

        # *** اہم تبدیلی: await کا استعمال کریں ***
        news_check = await check_news(symbol)
        news_impact = news_check.get("impact", "Clear")
        news_reason = news_check.get("reason", "No news check performed.")

        if news_impact == "High":
            return {
                "status": "blocked", "symbol": symbol, "signal": "wait",
                "reason": f"Trading BLOCKED: {news_reason}", "confidence": 0.0,
                "tier": "Tier 5 – Weak", "timeframe": timeframe, "price": closes[-1],
                "tp": None, "sl": None, "candles": candles
            }

        confidence = get_confidence(core_signal, pattern_data.get("type", "neutral"), risk_status, news_impact, symbol)
        tier = get_tier(confidence)
        reason = generate_reason(core_signal, pattern_data, risk_status, news_impact, confidence)
        
        tp_sl = calculate_tp_sl(core_signal, closes[-1], highs, lows)
        final_signal = core_signal
        
        result = {
            "status": "ok" if final_signal != "wait" else "no-signal",
            "symbol": symbol, "signal": final_signal, "pattern": pattern_data.get("pattern"),
            "risk": risk_status, "news": news_impact, "reason": reason,
            "confidence": round(confidence, 2), "tier": tier, "timeframe": timeframe,
            "price": closes[-1], "tp": tp_sl.get("tp"), "sl": tp_sl.get("sl"),
            "candles": candles
        }

        if final_signal in ["buy", "sell"]:
            add_active_signal(symbol, result)
            
        return result

    except Exception as e:
        traceback.print_exc()
        raise Exception(f"Error in AI fusion for {symbol}: {e}")
                
