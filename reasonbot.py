# filename: reasonbot.py

def generate_reason(core_signal: str, pattern_data: dict, risk_status: str, news_impact: str, confidence: float, market_structure: dict) -> str:
    """
    Generate a human-readable reason for AI-generated trade signals based on fused indicators.
    """
    reason_parts = []

    pattern_name = pattern_data.get("pattern", "No Specific Pattern")
    pattern_type = pattern_data.get("type", "neutral")

    if core_signal == "buy":
        reason_parts.append("Core strategy indicates a BUY opportunity.")
        if pattern_type == "bullish":
            reason_parts.append(f"A bullish pattern ({pattern_name}) provides confirmation.")
        if market_structure.get("trend") == "uptrend":
            reason_parts.append("Market structure confirms the uptrend.")
    elif core_signal == "sell":
        reason_parts.append("Core strategy indicates a SELL opportunity.")
        if pattern_type == "bearish":
            reason_parts.append(f"A bearish pattern ({pattern_name}) provides confirmation.")
        if market_structure.get("trend") == "downtrend":
            reason_parts.append("Market structure confirms the downtrend.")
    else:
        reason_parts.append("Current market conditions suggest a WAIT or neutral stance.")

    if risk_status != "Normal":
        reason_parts.append(f"Market risk is {risk_status.upper()}.")
    if news_impact != "Clear":
        reason_parts.append(f"{news_impact.upper()} impact news events are expected.")
    if confidence < 60:
        reason_parts.append(f"Overall confidence is LOW ({confidence:.2f}%).")

    return " ".join(reason_parts) if reason_parts else "AI analysis complete."
