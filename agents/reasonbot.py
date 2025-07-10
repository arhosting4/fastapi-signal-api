def generate_reason(core_signal: str, pattern_data: dict, risk_status: str, news_impact: str, confidence: float) -> str:
    reason_parts = []
    pattern_name = pattern_data.get("pattern", "No Specific Pattern")
    pattern_type = pattern_data.get("type", "neutral")
    if core_signal == "buy":
        reason_parts.append("Core strategy indicates a BUY opportunity.")
        if pattern_type == "bullish": reason_parts.append(f"A bullish pattern ({pattern_name}) provides confirmation.")
        elif pattern_type == "bearish": reason_parts.append(f"However, a bearish pattern ({pattern_name}) suggests caution.")
    elif core_signal == "sell":
        reason_parts.append("Core strategy indicates a SELL opportunity.")
        if pattern_type == "bearish": reason_parts.append(f"A bearish pattern ({pattern_name}) provides confirmation.")
        elif pattern_type == "bullish": reason_parts.append(f"However, a bullish pattern ({pattern_name}) suggests caution.")
    else:
        reason_parts.append("Current market conditions suggest a WAIT or neutral stance.")
    if risk_status != "Normal": reason_parts.append(f"Market risk is {risk_status.upper()}.")
    if news_impact != "Clear": reason_parts.append(f"{news_impact.upper()} impact news events are expected.")
    if confidence < 60: reason_parts.append(f"Overall confidence is LOW ({confidence:.2f}%).")
    return " ".join(reason_parts)
