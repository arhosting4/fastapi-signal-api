# src/agents/reasonbot.py

def generate_reason(core_signal: str, pattern_signal: str, confidence: float) -> str:
    """
    Generates a natural language reason for the signal decision
    based on core strategy, pattern recognition, and overall confidence.

    Parameters:
        core_signal (str): Signal from the core strategy logic ("buy", "sell", "wait").
        pattern_signal (str): Detected chart pattern (e.g., "Bullish Engulfing", "No Specific Pattern").
        confidence (float): The overall confidence score of the signal.

    Returns:
        str: A descriptive reason for the signal.
    """
    reason = ""

    # Evaluate core signal and pattern alignment
    if core_signal == "buy":
        if "Bullish" in pattern_signal or "Upward Momentum" in pattern_signal:
            reason = "Strong bullish signal confirmed by positive chart patterns."
        elif "Bearish" in pattern_signal or "Downward Momentum" in pattern_signal:
            reason = "Core strategy suggests buying, but bearish patterns indicate caution."
        else:
            reason = "Core strategy indicates a buy opportunity."
    elif core_signal == "sell":
        if "Bearish" in pattern_signal or "Downward Momentum" in pattern_signal:
            reason = "Strong bearish signal confirmed by negative chart patterns."
        elif "Bullish" in pattern_signal or "Upward Momentum" in pattern_signal:
            reason = "Core strategy suggests selling, but bullish patterns indicate a potential pullback."
        else:
            reason = "Core strategy indicates a sell opportunity."
    else: # core_signal == "wait"
        reason = "No clear signal from core strategy."
        if "No Specific Pattern" not in pattern_signal:
            reason += f" However, a '{pattern_signal}' pattern was observed."

    # Add confidence level to the reason
    if confidence >= 90:
        reason += " High confidence in this analysis."
    elif confidence >= 80:
        reason += " Good confidence in this analysis."
    elif confidence >= 70:
        reason += " Moderate confidence in this analysis."
    else:
        reason += " Further confirmation might be needed due to lower confidence."

    return reason
