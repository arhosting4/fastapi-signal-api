from strategybot import generate_core_signal, calculate_tp_sl
from patternai import detect_patterns
from riskguardian import check_risk
from sentinel import check_news
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from signal_tracker import add_active_signal
import traceback

def generate_final_signal(symbol: str, candles: list, timeframe: str):
    try:
        closes = [float(c["close"]) for c in candles]
        highs = [float(c["high"]) for c in candles]
        lows = [float(c["low"]) for c in candles]
        current_price = closes[-1] if closes else None

        core_signal = generate_core_signal(symbol, timeframe, closes)
        
        if core_signal == "wait" and len(closes) < 34:
            return {"status": "no-signal", "symbol": symbol, "signal": "wait", "reason": "Insufficient historical data.", "timeframe": timeframe, "price": current_price}

        pattern_data = detect_patterns(candles)
        risk_assessment = check_risk(candles)
        risk_status = risk_assessment.get("status", "Normal")

        if risk_status == "High":
            return {"status": "blocked", "symbol": symbol, "signal": "wait", "reason": f"Trading BLOCKED: {risk_assessment.get('reason')}", "timeframe": timeframe, "price": current_price}

        news_assessment = check_news(symbol)
        news_impact = news_assessment.get("impact", "Clear")
        
        confidence = get_confidence(core_signal, pattern_data.get("type", "neutral"), risk_status, news_impact)
        tier = get_tier(confidence)
        reason = generate_reason(core_signal, pattern_data, risk_status, news_impact, confidence)
        
        tp_sl_levels = {"tp": None, "sl": None}
        if current_price is not None:
            tp_sl_levels = calculate_tp_sl(core_signal, current_price, highs, lows)

        final_result = {
            "status": "ok", "symbol": symbol, "signal": core_signal,
            "pattern": pattern_data.get("pattern", "N/A"), "risk": risk_status, "news": news_impact,
            "reason": reason, "confidence": round(confidence, 2), "tier": tier,
            "timeframe": timeframe, "price": current_price,
            "tp": tp_sl_levels["tp"], "sl": tp_sl_levels["sl"]
        }

        if final_result["signal"] in ["buy", "sell"] and final_result["tp"] is not None:
            add_active_signal(final_result)

        return final_result
    except Exception as e:
        traceback.print_exc()
        raise Exception(f"Error in AI fusion for {symbol}: {e}")
        
