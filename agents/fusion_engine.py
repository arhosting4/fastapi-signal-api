from agents.strategybot import generate_core_signal
from agents.patternai import detect_patterns
from agents.riskguardian import check_risk
from agents.sentinel import check_news
from agents.reasonbot import generate_reason
from agents.trainerai import get_confidence # Import get_confidence
from agents.tierbot import get_tier

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

        # ✅ Convert candle data to closing prices list (for strategybot and riskguardian)
        # Note: pandas_ta in strategybot directly uses the list of closes.
        closes = [float(candle["close"]) for candle in candles]

        # ✅ Step 1: Core AI strategy signal
        strategy_signal = generate_core_signal(symbol, tf, closes)
        if not strategy_signal or strategy_signal == "wait":
            # If core strategy doesn't find a signal, we return no-signal
            # We can still calculate confidence for "wait" signals if needed,
            # but for now, we'll return no-signal directly.
            return {
                "status": "no-signal",
                "symbol": symbol,
                "signal": "wait",
                "reason": "Core strategy did not identify a clear trend.",
                "confidence": 50.0, # Default confidence for wait
                "tier": get_tier(50.0) # Default tier for wait
            }

        # ✅ Step 2: Detect chart pattern (currently dummy)
        pattern_data = detect_patterns(symbol, tf)
        pattern = pattern_data.get("pattern", "No Specific Pattern") # Default if no pattern

        # ✅ Step 3: Risk check (currently dummy)
        # You'll need to pass appropriate data to check_risk if it uses candles
        if check_risk(symbol, closes): # Assuming check_risk uses closes
            return {"status": "blocked", "error": "High market risk"}

        # ✅ Step 4: News filter (currently dummy)
        # (Empty list used for now — can integrate live news later)
        if check_news(symbol, []):
            return {"status": "blocked", "error": "Red news event"}

        # ✅ Step 5: Reasoning
        reason = generate_reason(strategy_signal, pattern)

        # ✅ Step 6: Confidence (UPDATED to pass candles)
        confidence = get_confidence(symbol, tf, strategy_signal, pattern, candles)

        # ✅ Step 7: Tier level
        tier = get_tier(confidence)

        # ✅ Step 8: Final signal result
        return {
            "status": "ok",
            "symbol": symbol,
            "signal": strategy_signal,
            "pattern": pattern,
            "risk": "Normal", # Placeholder, update after check_risk is real
            "news": "Clear", # Placeholder, update after check_news is real
            "reason": reason,
            "confidence": round(confidence, 2),
            "tier": tier
        }

    except Exception as e:
        print(f"Error in fusion_engine: {e}")
        return {"status": "error", "message": str(e)}
        
