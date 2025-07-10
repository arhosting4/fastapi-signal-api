from agents.strategybot import generate_core_signal, calculate_tp_sl
from agents.patternai import detect_patterns
from agents.riskguardian import check_risk
from agents.sentinel import check_news
from agents.reasonbot import generate_reason
from agents.trainerai import get_confidence
from agents.tierbot import get_tier
from agents.signal_tracker import add_active_signal # Import add_active_signal
import traceback # For detailed error logging

# Added 'timeframe' parameter
def generate_final_signal(symbol: str, candles: list, timeframe: str):
    """
    Core AI fusion engine combining all agents to generate a god-level trading signal.

    Parameters:
        symbol (str): The trading pair (e.g., XAU/USD).
        candles (list): List of OHLC candles from the API.
        timeframe (str): The timeframe of the candles (e.g., 1min, 5min). # New parameter

    Returns:
        dict: Final AI signal output with full intelligence context.
    """
    try:
        # Extract necessary data for calculations
        closes = [float(c["close"]) for c in candles]
        highs = [float(c["high"]) for c in candles]
        lows = [float(c["low"]) for c in candles]
        current_price = closes[-1] if closes else None # Get the last closing price

        # ✅ Step 1: Core AI strategy signal
        core_signal = generate_core_signal(symbol, timeframe, closes)
            
        # If core_signal is 'wait' due to insufficient data, return early
        if core_signal == "wait" and len(closes) < 34: # Based on strategybot's data requirement
            return {
                "status": "no-signal",
                "symbol": symbol,
                "signal": "wait",
                "pattern": "Insufficient Data",
                "risk": "Normal",
                "news": "Clear",
                "reason": "Insufficient historical data for a reliable signal.",
                "confidence": 50.0,
                "tier": "Tier 5 – Weak",
                "timeframe": timeframe,
                "price": current_price, # Include current price
                "tp": None,
                "sl": None
            }

        # ✅ Step 2: Detect chart pattern
        pattern_data = detect_patterns(candles)
        pattern_name = pattern_data.get("pattern", "No Specific Pattern")
        pattern_type = pattern_data.get("type", "neutral") # bullish, bearish, neutral

        # ✅ Step 3: Risk check
        risk_assessment = check_risk(candles)
        risk_status = risk_assessment.get("status", "Normal")
        risk_reason = risk_assessment.get("reason", "Market risk appears normal.")

        if risk_status == "High":
            return {
                "status": "blocked",
                "symbol": symbol,
                "signal": "wait", # Blocked signals are essentially 'wait'
                "pattern": pattern_name,
                "risk": risk_status,
                "news": "Clear", # News is checked separately
                "reason": f"Trading BLOCKED: {risk_reason}",
                "confidence": 0.0, # No confidence if blocked
                "tier": "Tier 5 – Weak",
                "timeframe": timeframe,
                "price": current_price, # Include current price
                "tp": None,
                "sl": None
            }

        # ✅ Step 4: News filter (Placeholder for now)
        news_impact = "Clear" # Default to clear for now
        news_reason = "No significant news events anticipated."
            
        # ✅ Step 5: Confidence
        confidence = get_confidence(
            core_signal,
            pattern_type, # Pass pattern_type (bullish, bearish, neutral)
            risk_status,
            news_impact
        )

        # ✅ Step 6: Tier level
        tier = get_tier(confidence)

        # ✅ Step 7: Reasoning
        reason = generate_reason(
            core_signal,
            pattern_data, # Pass pattern_data dict
            risk_status,
            news_impact,
            confidence
        )

        # ✅ Step 8: Calculate TP/SL
        tp_sl_levels = {"tp": None, "sl": None}
        if current_price is not None: # Only calculate if we have a current price
            tp_sl_levels = calculate_tp_sl(core_signal, current_price, highs, lows)


        # ✅ Step 9: Final signal result
        final_result = {
            "status": "ok", # Or "no-signal" if core_signal is "wait"
            "symbol": symbol,
            "signal": core_signal,
            "pattern": pattern_name,
            "risk": risk_status,
            "news": news_impact,
            "reason": reason,
            "confidence": round(confidence, 2),
            "tier": tier,
            "timeframe": timeframe,
            "price": current_price, # Include current price
            "tp": tp_sl_levels["tp"], # Include TP
            "sl": tp_sl_levels["sl"]  # Include SL
        }

        # ✅ Step 10: Add to signal tracker if it's a trade signal
        if final_result["signal"] in ["buy", "sell"] and final_result["tp"] is not None and final_result["sl"] is not None:
            add_active_signal(final_result)

        return final_result

    except Exception as e:
        # Log the full traceback for debugging
        print(f"CRITICAL ERROR in fusion_engine for {symbol}: {e}")
        traceback.print_exc()
        # Re-raise the exception to be caught by app.py's global handler
        raise Exception(f"Error in AI fusion for {symbol}: {e}")
        
