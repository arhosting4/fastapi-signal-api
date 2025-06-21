# src/agents/tierbot.py

def get_tier(confidence: float) -> str:
    """
    Determines AI tier level based on confidence score.

    Parameters:
        confidence (float): Confidence level (0-100%)

    Returns:
        str: Tier level (Tier 1, Tier 2, Tier 3, etc.)
    """
    if confidence >= 90:
        return "Tier 1 – Elite"
    elif confidence >= 80:
        return "Tier 2 – Strong"
    elif confidence >= 70:
        return "Tier 3 – Moderate"
    elif confidence >= 60:
        return "Tier 4 – Caution"
    else:
        return "Tier 5 – Weak"
