import random
import pandas as pd
import pandas_ta as ta # Import pandas_ta for indicator calculations

def get_confidence(pair: str, tf: str, core_signal: str, pattern_signal: str, candles: list) -> float:
    """
    Estimates signal confidence based on current logic fusion and indicator values.
    This version uses indicator values from the latest candles to provide a more
    meaningful confidence score.

    Parameters:
        pair (str): Trading pair symbol (e.g., XAU/USD)
        tf (str): Timeframe (e.g., 1min)
        core_signal (str): Signal from core strategy logic (buy/sell/wait)
        pattern_signal (str): Signal from pattern recognition agent (currently dummy)
        candles (list): List of OHLC candles from the API.

    Returns:
        float: Confidence percentage from 0% to 100%
    """
    confidence = 50.0 # Base confidence

    if not candles or len(candles) < 100: # Need enough data for indicators
        return confidence # Return base if not enough data

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

    # Adjust confidence based on core signal and indicator alignment
    if core_signal == "buy":
        # Stronger buy signal if RSI is low (oversold), MACD is bullish, and price is near lower BB
        if rsi < 40: # More oversold
            confidence += 10
        if macd_line > signal_line: # MACD bullish
            confidence += 10
            if macd_line > 0: # MACD above zero line
                confidence += 5
        if latest_close <= bb_lower: # Price touching/below lower band
            confidence += 15
        elif latest_close < bbands[bbands.columns[1]].iloc[-1]: # Price below middle band
            confidence += 5
            
        # Penalize if RSI is too high or MACD is bearish
        if rsi > 70:
            confidence -= 15
        if macd_line < signal_line:
            confidence -= 10

    elif core_signal == "sell":
        # Stronger sell signal if RSI is high (overbought), MACD is bearish, and price is near upper BB
        if rsi > 60: # More overbought
            confidence += 10
        if macd_line < signal_line: # MACD bearish
            confidence += 10
            if macd_line < 0: # MACD below zero line
                confidence += 5
        if latest_close >= bb_upper: # Price touching/above upper band
            confidence += 15
        elif latest_close > bbands[bbands.columns[1]].iloc[-1]: # Price above middle band
            confidence += 5

        # Penalize if RSI is too low or MACD is bullish
        if rsi < 30:
            confidence -= 15
        if macd_line > signal_line:
            confidence -= 10

    # Adjust based on pattern signal (currently dummy, but can be expanded)
    if core_signal == pattern_signal and core_signal != "wait":
        confidence += 5 # Small bonus for alignment

    # Ensure confidence is within 0-100 range
    confidence = max(0.0, min(100.0, confidence))

    return round(confidence, 2)
    
