# src/agents/fusion_engine.py

# Import all necessary agents
from src.agents.strategybot import generate_core_signal
from src.agents.patternai import detect_patterns
from src.agents.riskguardian import check_risk
from src.agents.sentinel import check_news
from src.agents.reasonbot import generate_reason
from src.agents.trainerai import get_confidence
from src.agents.tierbot import get_tier

def generate_final_signal(symbol: str, candles: list) -> dict:
    """
    Core AI fusion engine combining all agents to generate a comprehensive trading signal.

    Parameters:
        symbol (str): The trading pair (e.g., XAU/USD).
        candles (list): List of OHLC candles, from oldest to newest.
                        Each candle is expected to be a dictionary with 'open', 'high', 'low', 'close' as strings.

    Returns:
        dict: Final AI signal output with full intelligence context.
    """
    try:
        if not candles or len(candles) < 5: # Ensure enough data for analysis
            return {"status": "error", "message": "Insufficient candle data for analysis."}

        # Convert candle data to closing prices list (as floats)
        # Assuming candles are ordered oldest to newest
        closes = [float(candle["close"]) for candle in candles]
        
        # Define timeframe (can be passed as parameter if needed)
        tf = "1min" 

        # ✅ Step 1: Core AI strategy signal
        # This uses the 'closes' list
        strategy_signal = generate_core_signal(symbol, tf, closes)
        
        # If core strategy doesn't give a clear signal, we might stop here or proceed with caution
        if strategy_signal == "wait":
            return {
                "status": "no-signal",
                "symbol": symbol,
                "signal": "wait",
                "reason": "Core strategy did not identify a clear trend.",
                "confidence": 50.0, # Default confidence for no signal
                "tier": get_tier(50.0)
            }

        # ✅ Step 2: Detect chart pattern
        # This uses the full 'candles' list
        pattern_data = detect_patterns(symbol, tf, candles)
        pattern_name = pattern_data.get("pattern", "No Specific Pattern")
        
        # ✅ Step 3: Risk check
        # This uses the 'closes' list
        is_risky = check_risk(symbol, closes)
        if is_risky:
            return {
                "status": "blocked",
                "symbol": symbol,
                "signal": "blocked",
                "error": "High market risk detected (volatility).",
                "risk": "High",
                "confidence": 0.0,
                "tier": get_tier(0.0)
            }

        # ✅ Step 4: News filter
        # (Empty list used for now – integrate live news later)
        # This uses a dummy empty list for high_impact_events
        is_news_event = check_news(symbol, []) # Pass an empty list for now
        if is_news_event:
            return {
                "status": "blocked",
                "symbol": symbol,
                "signal": "blocked",
                "error": "Red news event detected.",
                "news": "Red Alert",
                "confidence": 0.0,
                "tier": get_tier(0.0)
            }

        # ✅ Step 5: Confidence Calculation
        # This uses the core signal and pattern data
        confidence = get_confidence(symbol, tf, strategy_signal, pattern_data)

        # ✅ Step 6: Tier level
        # This uses the calculated confidence
        tier = get_tier(confidence)

        # ✅ Step 7: Reasoning
        # This uses core signal, pattern name, and confidence
        reason = generate_reason(strategy_signal, pattern_name, confidence)

        # ✅ Step 8: Final signal result
        return {
            "status": "ok",
            "symbol": symbol,
            "signal": strategy_signal,
            "pattern": pattern_name,
            "risk": "Normal" if not is_risky else "High", # Reflect actual risk status
            "news": "Clear" if not is_news_event else "Red Alert", # Reflect actual news status
            "reason": reason,
            "confidence": round(confidence, 2),
            "tier": tier
        }

    except Exception as e:
        print(f"❌ Error in fusion engine for {symbol}: {e}")
        return {"status": "error", "message": str(e)}

