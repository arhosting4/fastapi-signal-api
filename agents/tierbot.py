# src/agents/tierbot.py

def assign_tier(symbol: str, confidence: float, risk: str, bias: str) -> str:
    """
    Assigns a signal Tier (1 to 4) based on confidence, risk level, and market bias.
    Higher tier = more trustworthy signal.
    """

    # Base scoring model
    score = 0

    # Confidence scoring
    if confidence >= 0.85:
        score += 2
    elif confidence >= 0.65:
        score += 1

    # Risk scoring
    if risk == "low":
        score += 2
    elif risk == "medium":
        score += 1
    elif risk == "high":
        score -= 1

    # Bias influence
    if bias == "bullish" or bias == "bearish":
        score += 1
    elif bias == "neutral":
        score -= 1

    # Final tier assignment
    if score >= 5:
        return "Tier 1 🚀"
    elif score >= 3:
        return "Tier 2 ⚡"
    elif score >= 1:
        return "Tier 3 ⚠️"
    else:
        return "Tier 4 ❄️"
