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
    """
    Core AI fusion engine combining all agents to generate a trading signal.
    """
    try:
        # Extract necessary data for calculations
        closes = [float(c["close"]) for c in candles]
        highs = [float(c["high"]) for c in candles]
        lows = [float(c["low"]) for c in candles]
        current_price = closes[-1] if closes else None

        # Step 1: Core AI strategy signal
        core_signal = generate_core_signal(symbol, timeframe, closes)
        
        # Handle case of insufficient data early
        if core_signal == "wait" and len(closes) < 34:
            return {
                "status": "no-signal", "symbol": symbol, "signal": "wait",
                "reason": "Insufficient historical data for a reliable signal.",
                "timeframe": timeframe, "price": current_price, "tp": None, "sl": None
            }

        # Step 2: Detect chart pattern
        pattern_data = detect_patterns(candles)
        pattern_type = pattern_data.get("type", "neutral")
        pattern_name = pattern_data.get("pattern", "No Specific Pattern")

        # Step 3: Risk check
        risk_assessment = check_risk(candles)
        risk_status = risk_assessment.get("status", "Normal")
        risk_reason = risk_assessment.get("reason", "Market risk appears normal.")

        # Block trade if risk is high
        if risk_status == "High":
            return {
                "status": "blocked", "symbol": symbol, "signal": "wait",
                "reason": f"Trading BLOCKED: {risk_reason}",
                "timeframe": timeframe, "price": current_price, "tp": None, "sl": None
            }

        # Step 4: News filter
        news_assessment = check_news(symbol)
        news_impact = news_assessment.get("impact", "Clear")
        
        # Step 5: Confidence Calculation (Now with feedback)
        # Pass the symbol to get_confidence for feedback-based adjustment
        confidence = get_confidence(symbol, core_signal, pattern_type, risk_status, news_impact)
        
        # Step 6: Tier level
        tier = get_tier(confidence)
        
        # Step 7: Reasoning
        reason = generate_reason(core_signal, pattern_data, risk_status, news_impact, confidence)
        
        # Step 8: Calculate TP/SL
        tp_sl_levels = {"tp": None, "sl": None}
        if current_price is not None:
            tp_sl_levels = calculate_tp_sl(core_signal, current_price, highs, lows)

        # Step 9: Final signal result
        final_result = {
            "status": "ok" if core_signal != "wait" else "no-signal",
            "symbol": symbol,
            "signal": core_signal,
            "pattern": pattern_name,
            "risk": risk_status,
            "news": news_impact,
            "reason": reason,
            "confidence": round(confidence, 2),
            "tier": tier,
            "timeframe": timeframe,
            "price": current_price,
            "tp": tp_sl_levels["tp"],
            "sl": tp_sl_levels["sl"]
        }

        # Step 10: Add to signal tracker if it's a trade signal
        if final_result["signal"] in ["buy", "sell"] and final_result["tp"] is not None:
            add_active_signal(final_result)

        return final_result

    except Exception as e:
        print(f"CRITICAL ERROR in fusion_engine for {symbol}: {e}")
        traceback.print_exc()
        raise Exception(f"Error in AI fusion for {symbol}: {e}")
        
