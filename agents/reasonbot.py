# src/agents/reasonbot.py

def generate_reasoning(symbol: str, signal: str, pattern: str, risk: str, confidence: float) -> str:
    """
    Creates a reasoning summary for the generated signal.
    """
    try:
        reason_parts = []

        if signal == "buy":
            reason_parts.append("upward momentum detected")
        elif signal == "sell":
            reason_parts.append("downward momentum observed")
        else:
            reason_parts.append("no strong market direction")

        if pattern == "bullish":
            reason_parts.append("pattern confirms buying pressure")
        elif pattern == "bearish":
            reason_parts.append("pattern supports selling trend")
        else:
            reason_parts.append("pattern is unclear")

        reason_parts.append(f"risk is {risk}")
        reason_parts.append(f"confidence score is {round(confidence * 100, 2)}%")

        return " | ".join(reason_parts)
    except Exception:
        return "Could not generate reasoning"
