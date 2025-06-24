# src/agents/tierbot.py

def classify_signal_tier(confidence: float, pattern: str) -> str:
    """
    Classifies signal into tiers based on confidence and pattern.
    """
    try:
        if confidence >= 0.02 and pattern == "bullish":
            return "Tier 1"
        elif confidence >= 0.015 and pattern == "bearish":
            return "Tier 2"
        elif confidence >= 0.01:
            return "Tier 3"
        else:
            return "Tier 4"
    except Exception:
        return "Unknown"
