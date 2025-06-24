# src/agents/reasonbot.py

def assess_context(symbol: str) -> dict:
    """
    Analyzes market context (mock implementation).
    Later can include news, correlation, and volatility.
    """
    # Placeholder logic
    if "XAU" in symbol:
        trend = "bullish"
        strength = 0.8
    else:
        trend = "neutral"
        strength = 0.5

    return {
        "trend": trend,
        "strength": strength,
        "confidence": strength * 100
    }
