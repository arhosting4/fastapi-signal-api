# src/agents/reasonbot.py

def generate_reasoning(signal: str, pattern: str, risk: str) -> str:
    """
    Generates a logical reason for the signal based on AI evaluations.
    """

    if signal == "buy":
        if pattern == "bullish_engulfing":
            return "Bullish engulfing pattern confirms buying opportunity with low resistance."
        elif risk == "low":
            return "Low risk and upward momentum support a buy setup."
        else:
            return "Momentum favors buying despite pattern uncertainty."

    elif signal == "sell":
        if pattern == "bearish_engulfing":
            return "Bearish engulfing signals strong downward reversal, confirming sell bias."
        elif risk == "low":
            return "Low risk environment allows safe shorting opportunity."
        else:
            return "Bearish conditions despite weak pattern, caution advised."

    return "Market conditions unclear, signal is uncertain."
