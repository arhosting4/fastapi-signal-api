# src/agents/tierbot.py

def assign_signal_tier(pattern: str, risk: str, signal: str) -> str:
    """
    Assigns a confidence tier: 'A' (high), 'B' (medium), 'C' (low)
    based on pattern accuracy and risk context.
    """

    if signal == "wait":
        return "C"

    if pattern in ["bullish_engulfing", "bearish_engulfing"] and risk == "low":
        return "A"
    elif risk == "medium":
        return "B"
    else:
        return "C"
