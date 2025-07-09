import pandas as pd
import pandas_ta as ta

def generate_reason(core_signal: str, pattern_data: dict, candles: list) -> str:
    """
    Generates a natural language reason for the signal decision based on
    core strategy, pattern recognition, and indicator states.

    Parameters:
        core_signal (str): Signal from core strategy logic (buy/sell/wait).
        pattern_data (dict): Dictionary from patternai containing 'pattern' and 'confidence'.
        candles (list): List of OHLC candles from the API.

    Returns:
        str: A detailed reason for the signal.
    """
    reason_parts = []
    pattern = pattern_data.get("pattern", "No Specific Pattern")
    pattern_confidence = pattern_data.get("confidence", 0.5)

    # --- Indicator Analysis for Reasoning ---
    if not candles or len(candles) < 100:
        return "Not enough data for detailed reasoning."

    close_series = pd.Series([c['close'] for c in candles])
        
    # Calculate Indicators
    rsi = ta.rsi(close_series, length=14).iloc[-1]
    macd = ta.macd(close_series, fast=12, slow=26, signal=9)
    macd_line = macd[macd.columns[0]].iloc[-1]
    signal_line = macd[macd.columns[1]].iloc[-1]
        
    bbands = ta.bbands(close_series, length=20, std=2)
    bb_lower = bbands[bbands.columns[0]].iloc[-1]
    bb_upper = bbands[bbands.columns[2]].iloc[-1]
    latest_close = close_series.iloc[-1]

    # --- Core Signal Reasoning ---
    if core_signal == "buy":
        reason_parts.append("Core strategy indicates a *BUY* opportunity.")
        if rsi < 30:
            reason_parts.append(f"RSI ({rsi:.2f}) is in oversold territory, suggesting a potential rebound.")
        elif rsi < 50:
            reason_parts.append(f"RSI ({rsi:.2f}) is below 50, indicating bearish momentum might be weakening.")
            
        if macd_line > signal_line:
            reason_parts.append("MACD shows a bullish crossover, confirming upward momentum.")
            if macd_line > 0:
                reason_parts.append("MACD is above the zero line, reinforcing bullish sentiment.")
            
        if latest_close <= bb_lower:
            reason_parts.append("Price is touching or below the Bollinger Lower Band, suggesting it's undervalued.")
        elif latest_close < bbands[bbands.columns[1]].iloc[-1]:
            reason_parts.append("Price is below the Bollinger Middle Band, but showing signs of recovery.")

    elif core_signal == "sell":
        reason_parts.append("Core strategy indicates a *SELL* opportunity.")
        if rsi > 70:
            reason_parts.append(f"RSI ({rsi:.2f}) is in overbought territory, suggesting a potential pullback.")
        elif rsi > 50:
            reason_parts.append(f"RSI ({rsi:.2f}) is above 50, indicating bullish momentum might be weakening.")
            
        if macd_line < signal_line:
            reason_parts.append("MACD shows a bearish crossover, confirming downward momentum.")
            if macd_line < 0:
                reason_parts.append("MACD is below the zero line, reinforcing bearish sentiment.")
            
        if latest_close >= bb_upper:
            reason_parts.append("Price is touching or above the Bollinger Upper Band, suggesting it's overvalued.")
        elif latest_close > bbands[bbands.columns[1]].iloc[-1]:
            reason_parts.append("Price is above the Bollinger Middle Band, but showing signs of decline.")

    else: # core_signal == "wait"
        reason_parts.append("Market is currently neutral or lacks clear signals.")
        if 40 <= rsi <= 60:
            reason_parts.append(f"RSI ({rsi:.2f}) is near the neutral zone.")
        if abs(macd_line - signal_line) < 0.01: # Small difference
            reason_parts.append("MACD lines are converging or flat, indicating indecision.")
        if bb_lower < latest_close < bb_upper:
            reason_parts.append("Price is within Bollinger Bands, suggesting consolidation.")

    # --- Pattern Reasoning ---
    if pattern != "No Specific Pattern":
        if core_signal == "buy" and ("Bullish" in pattern or "Morning Star" in pattern or "Hammer" in pattern or "Piercing" in pattern):
            reason_parts.append(f"A *{pattern}* candlestick pattern is detected, reinforcing the buy signal.")
        elif core_signal == "sell" and ("Bearish" in pattern or "Evening Star" in pattern or "Hanging Man" in pattern or "Dark Cloud Cover" in pattern):
            reason_parts.append(f"A *{pattern}* candlestick pattern is detected, reinforcing the sell signal.")
        else:
            reason_parts.append(f"A *{pattern}* candlestick pattern is detected, but its alignment with the core signal is mixed.")
    else:
        reason_parts.append("No significant candlestick pattern identified.")

    # Combine all parts into a single reason
    return " ".join(reason_parts)
    
