# src/agents/trainerai.py

import random

def get_confidence(pair: str, tf: str, core_signal: str, pattern_data: dict) -> float:
    """
    Estimates signal confidence based on current logic fusion.
    In a future upgrade, this will use adaptive ML training logs and historical performance.

    Parameters:
        pair (str): Trading pair symbol (e.g., XAU/USD).
        tf (str): Timeframe (e.g., 1min).
        core_signal (str): Signal from core strategy logic ("buy", "sell", "wait").
        pattern_data (dict): Dictionary containing pattern and its confidence
                             (e.g., {"pattern": "Bullish Engulfing", "confidence": 0.82}).

    Returns:
        float: Confidence percentage from 0% to 100%.
    """
    pattern_name = pattern_data.get("pattern", "No Specific Pattern")
    pattern_confidence = pattern_data.get("confidence", 0.0)

    base_confidence = 50.0 # Starting point for confidence

    # Adjust confidence based on core signal and pattern alignment
    if core_signal in ["buy", "sell"]:
        if (core_signal == "buy" and ("Bullish" in pattern_name or "Upward Momentum" in pattern_name)) or \
           (core_signal == "sell" and ("Bearish" in pattern_name or "Downward Momentum" in pattern_name)):
            # Strong agreement between core signal and pattern
            base_confidence += 30 # Significant boost
            base_confidence += (pattern_confidence * 20) # Add more based on pattern's own confidence
        elif core_signal != "wait" and "No Specific Pattern" not in pattern_name:
            # Core signal exists, but pattern is mixed or conflicting
            base_confidence -= 10 # Slight reduction for conflict
            base_confidence += (pattern_confidence * 10) # Still consider pattern's confidence
        else:
            # Core signal exists, but no specific pattern detected
            base_confidence += 5 # Small boost for core signal
    else: # core_signal == "wait"
        base_confidence -= 20 # Lower confidence if core strategy is waiting

    # Add a small random factor for variability (for now)
    random_factor = random.uniform(-5, 5)
    final_confidence = base_confidence + random_factor

    # Ensure confidence is within 0-100 range
    final_confidence = max(0.0, min(100.0, final_confidence))

    return round(final_confidence, 2)

