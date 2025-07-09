import random

def get_confidence(pair: str, tf: str, core: str, pattern: str, pattern_confidence: float = 0.0) -> float:
    """
    Estimates signal confidence based on current logic fusion.
    In a future upgrade, this will use adaptive ML training logs.

    Parameters:
        pair (str): Trading pair symbol (e.g., XAU/USD)
        tf (str): Timeframe (e.g., 1min)
        core (str): Signal from core strategy logic (buy/sell/wait)
        pattern (str): Detected pattern (e.g., "Bullish Engulfing", "No Specific Pattern")
        pattern_confidence (float): Confidence score from pattern detection (0.0-1.0)

    Returns:
        float: Confidence percentage from 0% to 100%
    """
    base_confidence = 50.0 # Starting point for confidence

    # Adjust based on core strategy and pattern agreement
    if core == "buy" and "Bullish" in pattern:
        base_confidence += 20 # Strong agreement
    elif core == "sell" and "Bearish" in pattern:
        base_confidence += 20 # Strong agreement
    elif core == "wait" and pattern == "No Specific Pattern":
        base_confidence -= 10 # Less confident if no clear pattern and wait signal
    elif (core == "buy" and "Bearish" in pattern) or \
         (core == "sell" and "Bullish" in pattern):
        base_confidence -= 15 # Conflicting signals, reduce confidence

    # Incorporate pattern_confidence from patternai
    # Scale pattern_confidence (0.0-1.0) to a range (e.g., 0-20) and add it
    base_confidence += (pattern_confidence * 20) 

    # Add some randomness for initial simulation, will be replaced by ML
    final_confidence = round(random.uniform(max(0, base_confidence - 5), min(100, base_confidence + 5)), 2)
        
    # Ensure confidence is within 0-100 range
    return max(0.0, min(100.0, final_confidence))

