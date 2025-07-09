from agents.strategybot import generate_core_signal
from agents.patternai import detect_patterns
from agents.riskguardian import check_risk # Import check_risk
from agents.sentinel import check_news # Import check_news
from agents.reasonbot import generate_reason
from agents.trainerai import get_confidence
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

        # Ensure we have enough candles for analysis
        if not candles or len(candles) < 100: # Minimum for strategybot, also good for patterns/risk
            return {
                "status": "no-signal",
                "symbol": symbol,
                "signal": "wait",
                "reason": "Not enough data for analysis.",
                "confidence": 50.0,
                "tier": get_tier(50.0)
            }

        # ✅ Step 1: Risk check (UPDATED to pass candles)
        if check_risk(symbol, candles): # Pass full candles to riskguardian
            return {"status": "blocked", "error": "High market risk detected."}

        # ✅ Step 2: News filter (UPDATED to pass symbol, though not fully used yet)
        if check_news(symbol): # Pass symbol to sentinel
            return {"status": "blocked", "error": "High-impact news event or risky hours detected."}

        # ✅ Step 3: Core AI strategy signal
        # Convert candle data to closing prices list for strategybot (if needed, pandas_ta handles DataFrames)
        closes = [float(candle["close"]) for candle in candles] # Still useful for some agents

        strategy_signal = generate_core_signal(symbol, tf, closes)
            
        # If core strategy doesn't find a signal, we return no-signal
        if not strategy_signal or strategy_signal == "wait":
            return {
                "status": "no-signal",
                "symbol": symbol,
                "signal": "wait",
                "reason": "Core strategy did not identify a clear trend.",
                "confidence": 50.0,
                "tier": get_tier(50.0)
            }

        # ✅ Step 4: Detect chart pattern
        pattern_data = detect_patterns(symbol, tf, candles) # Pass full candles to patternai
        pattern = pattern_data.get("pattern", "No Specific Pattern") # Default if no pattern

        # ✅ Step 5: Reasoning
        reason = generate_reason(strategy_signal, pattern)

        # ✅ Step 6: Confidence
        confidence = get_confidence(symbol, tf, strategy_signal, pattern, candles)

        # ✅ Step 7: Tier level
        tier = get_tier(confidence)

        # ✅ Step 8: Final signal result
        return {
            "status": "ok",
            "symbol": symbol,
            "signal": strategy_signal,
            "pattern": pattern,
            "risk": "High" if check_risk(symbol, candles) else "Normal", # Reflect actual risk status
            "news": "Risky" if check_news(symbol) else "Clear", # Reflect actual news status
            "reason": reason,
            "confidence": round(confidence, 2),
            "tier": tier
        }

    except Exception as e:
        print(f"Error in fusion_engine: {e}")
        return {"status": "error", "message": str(e)}
        
