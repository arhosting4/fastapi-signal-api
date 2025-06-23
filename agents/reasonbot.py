# src/agents/reasonbot.py

def generate_reason(signal: str, pattern: str, risk: str, tier: str, news: str) -> str:
    """
    Generates a natural language explanation for the AI's signal decision.
    Tailored to signal type, pattern confidence, risk level, and external factors.
    """
    reason = ""

    if signal == "buy":
        reason += "The system detected bullish conditions "
    elif signal == "sell":
        reason += "The system identified bearish momentum "
    else:
        reason += "The current market is indecisive "

    if pattern != "No pattern":
        reason += f"based on the presence of a '{pattern}' pattern, "
    else:
        reason += "without a clear pattern, "

    reason += f"which aligns with a '{tier}' confidence tier. "

    if risk == "Low Risk":
        reason += "The market shows stable volatility, making this signal relatively safe. "
    elif risk == "Moderate Risk":
        reason += "There is some volatility, so caution is advised. "
    elif risk == "High Risk":
        reason += "The market is highly volatile, increasing the risk level. "

    if news and news != "None":
        reason += f"News context: {news}. "

    return reason.strip()
