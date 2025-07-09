# src/agents/fusion_engine.py
from agents.strategybot import generate_core_signal
from agents.patternai import detect_patterns
from agents.riskguardian import check_risk
from agents.sentinel import check_news
from agents.reasonbot import generate_reason
from agents.trainerai import get_confidence
from agents.tierbot import get_tier
import traceback # For detailed error logging

def generate_final_signal(symbol: str, candles: list):
    """
    Core AI fusion engine combining all agents to generate a god-level trading signal.

    Parameters:
        symbol (str): The trading pair (e.g., XAU/USD).
        candles (list): List of OHLC candles from the API.

    Returns:
        dict: Final AI signal output with full intelligence context.
    """
    try:
        tf = "1min" # Timeframe is fixed for now

        # ✅ Step 1: Core AI strategy signal
        # strategybot now directly takes closes
        closes = [float(c['close']) for c in candles]
        strategy_signal = generate_core_signal(symbol, tf, closes)
            
        # If strategy_signal is 'wait' due to insufficient data, return early
        if strategy_signal == "wait" and len(closes) < 34: # Based on strategybot's data requirement
            return {
                "status": "no-signal",
                "symbol": symbol,
                "signal": "wait",
                "pattern": "Insufficient Data",
                "risk": "Normal",
                "news": "Clear",
                "reason": "Insufficient historical data for a reliable signal.",
                "confidence": 50.0,
                "tier": "Tier 5 – Weak"
            }

        # ✅ Step 2: Detect chart pattern
        # patternai now takes full candles DataFrame
        pattern_data = detect_patterns(candles)
        pattern_name = pattern_data.get("pattern", "No Specific Pattern")
        pattern_type = pattern_data.get("type", "neutral") # bullish, bearish, neutral

        # ✅ Step 3: Risk check
        # riskguardian now takes full candles DataFrame
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
                "tier": "Tier 5 – Weak"
            }

        # ✅ Step 4: News filter (Placeholder for now)
        # In a real scenario, this would fetch live news data
        # For now, we'll simulate a "Clear" news impact
        news_impact = "Clear" # Default to clear for now
        news_reason = "No significant news events anticipated."
            
        # Example of how you might integrate check_news if you had real data
        # high_impact_events = [] # Populate this from a news API
        # if check_news(symbol, high_impact_events):
        #     news_impact = "High"
        #     news_reason = "Red news event detected. Trading might be volatile."
        #     return {
        #         "status": "blocked",
        #         "symbol": symbol,
        #         "signal": "wait",
        #         "pattern": pattern_name,
        #         "risk": risk_status,
        #         "news": news_impact,
        #         "reason": f"Trading BLOCKED: {news_reason}",
        #         "confidence": 0.0,
        #         "tier": "Tier 5 – Weak"
        #     }


        # ✅ Step 5: Confidence
        # trainerai now takes more parameters
        confidence = get_confidence(
            core_signal,
            pattern_type, # Pass pattern_type (bullish, bearish, neutral)
            risk_status,
            news_impact
        )

        # ✅ Step 6: Tier level
        tier = get_tier(confidence)

        # ✅ Step 7: Reasoning
        # reasonbot now takes more parameters
        reason = generate_reason(
            core_signal,
            pattern_data, # Pass pattern_data dict
            risk_status,
            news_impact,
            confidence
        )

        # ✅ Step 8: Final signal result
        return {
            "status": "ok", # Or "no-signal" if core_signal is "wait"
            "symbol": symbol,
            "signal": strategy_signal,
            "pattern": pattern_name,
            "risk": risk_status,
            "news": news_impact,
            "reason": reason,
            "confidence": round(confidence, 2),
            "tier": tier
        }

    except Exception as e:
        # Log the full traceback for debugging
        print(f"CRITICAL ERROR in fusion_engine for {symbol}: {e}")
        traceback.print_exc()
        # Re-raise the exception to be caught by app.py's global handler
        raise Exception(f"Error in AI fusion for {symbol}: {e}")

