# src/agents/fusion_engine.py

from agents.strategybot import generate_core_signal
from agents.patternai import detect_patterns
from agents.riskguardian import check_risk
from agents.sentinel import check_news
from agents.reasonbot import generate_reason
from agents.trainerai import get_confidence
from agents.tierbot import get_tier
import pandas as pd # Import pandas for potential future use or debugging
import traceback # Import traceback module for detailed error logging

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
        tf = "1min" # Timeframe is now derived from candles or fixed

        # Ensure candles are sorted oldest to newest for proper TA-Lib/pandas_ta calculation
        # Assuming candles are already oldest to newest from fetch_real_ohlc_data
            
        # Extract closing prices for strategy and risk checks
        closes = [float(candle["close"]) for candle in candles]
            
        # Ensure enough data for calculations
        # Many indicators and patterns require a minimum number of candles (e.g., 20 for some MAs, 14 for RSI)
        if len(candles) < 20: 
            return {"status": "no-signal", "error": "Insufficient data for analysis.", "reason": "Not enough historical data to generate a reliable signal."}

        # ✅ Step 1: Core AI strategy signal
        strategy_signal = generate_core_signal(symbol, tf, closes)
        if not strategy_signal or strategy_signal == "wait":
            return {"status": "no-signal", "error": "Strategy failed or no trend", "reason": "Core strategy did not identify a clear trend."}

        # ✅ Step 2: Detect chart pattern
        # Pass the full candles list to patternai
        pattern_data = detect_patterns(candles) # Corrected: Pass only candles
        pattern = pattern_data.get("pattern", "Unknown")
        pattern_confidence = pattern_data.get("confidence", 0.0) # Get confidence from pattern detection

        # ✅ Step 3: Risk check
        # Pass the full candles list to riskguardian for more detailed analysis if needed
        if check_risk(symbol, closes): # Using closes for basic risk check
            return {"status": "blocked", "error": "High market risk", "reason": "Market volatility is too high or price movement is erratic."}

        # ✅ Step 4: News filter
        # (Empty list used for now — can integrate live news later)
        # You might want to pass symbol and current time to check for relevant news
        if check_news(symbol, []): # Assuming check_news uses symbol to filter events
            return {"status": "blocked", "error": "Red news event", "reason": "High-impact news event detected for this symbol."}

        # ✅ Step 5: Reasoning
        # Pass both strategy signal and detected pattern for a more nuanced reason
        reason = generate_reason(strategy_signal, pattern)

        # ✅ Step 6: Confidence
        # Use pattern_confidence along with strategy signal for overall confidence
        confidence = get_confidence(symbol, tf, strategy_signal, pattern, pattern_confidence)

        # ✅ Step 7: Tier level
        tier = get_tier(confidence)

        # ✅ Step 8: Final signal result
        return {
            "symbol": symbol,
            "signal": strategy_signal,
            "pattern": pattern,
            "risk": "Normal", # Update based on actual check_risk output if it returns more detail
            "news": "Clear", # Update based on actual check_news output if it returns more detail
            "reason": reason,
            "confidence": round(confidence, 2),
            "tier": tier,
            # You might want to add current price here if available from candles
            "price": float(candles[-1]["close"]) if candles else None # Add current price
        }

    except Exception as e:
        print(f"CRITICAL ERROR in fusion_engine for {symbol}: {e}")
        traceback.print_exc() # This will print the full traceback to the logs
        return {"status": "error", "message": f"An internal AI error occurred: {e}"}

