# src/agents/reasonbot.py

def generate_reason(
    core_signal: str,
    pattern_data: dict, # Now a dict from patternai
    risk_status: str,
    news_impact: str,
    confidence: float
) -> str:
    """
    Generates a natural language reason for the signal decision
    based on core strategy, pattern alignment, risk, news, and confidence.

    Parameters:
        core_signal (str): Signal from core strategy logic ("buy", "sell", "wait").
        pattern_data (dict): Dictionary from patternai with 'pattern' and 'type'.
        risk_status (str): Risk assessment from riskguardian ("Normal", "Moderate", "High").
        news_impact (str): News impact assessment from sentinel ("Clear", "Low", "Medium", "High").
        confidence (float): Overall confidence score.

    Returns:
        str: A descriptive reason for the signal.
    """
    reason_parts = []

    # --- Core Signal and Pattern Alignment ---
    pattern_name = pattern_data.get("pattern", "No Specific Pattern")
    pattern_type = pattern_data.get("type", "neutral")

    if core_signal == "buy":
        reason_parts.append("Core strategy indicates a BUY opportunity.")
        if pattern_type == "bullish":
            reason_parts.append(f"A strong bullish pattern ({pattern_name}) provides further confirmation.")
        elif pattern_type == "bearish":
            reason_parts.append(f"However, a bearish pattern ({pattern_name}) suggests caution.")
        else:
            reason_parts.append("No significant candlestick pattern detected for additional confirmation.")
    elif core_signal == "sell":
        reason_parts.append("Core strategy indicates a SELL opportunity.")
        if pattern_type == "bearish":
            reason_parts.append(f"A strong bearish pattern ({pattern_name}) provides further confirmation.")
        elif pattern_type == "bullish":
            reason_parts.append(f"However, a bullish pattern ({pattern_name}) suggests caution.")
        else:
            reason_parts.append("No significant candlestick pattern detected for additional confirmation.")
    else: # core_signal == "wait"
        reason_parts.append("Current market conditions suggest a WAIT or neutral stance.")
        if pattern_type != "neutral":
            reason_parts.append(f"A {pattern_type} pattern ({pattern_name}) was observed, but core strategy remains neutral.")
        else:
            reason_parts.append("No strong directional signals or patterns identified.")

    # --- Risk Assessment ---
    if risk_status == "High":
        reason_parts.append(f"Market risk is HIGH due to {risk_status.lower()} volatility/price action.")
    elif risk_status == "Moderate":
        reason_parts.append(f"Market risk is MODERATE due to {risk_status.lower()} volatility/price action.")
    else:
        reason_parts.append("Market risk appears normal.")

    # --- News Impact ---
    if news_impact == "High":
        reason_parts.append("High-impact news events are expected, increasing uncertainty.")
    elif news_impact == "Medium":
        reason_parts.append("Medium-impact news events are expected.")
    elif news_impact == "Low":
        reason_parts.append("Low-impact news events are expected.")
    else:
        reason_parts.append("No significant news events are anticipated.")

    # --- Confidence Level ---
    if confidence >= 80:
        reason_parts.append(f"Overall confidence is HIGH ({confidence:.2f}%).")
    elif confidence >= 60:
        reason_parts.append(f"Overall confidence is MODERATE ({confidence:.2f}%).")
    else:
        reason_parts.append(f"Overall confidence is LOW ({confidence:.2f}%).")

    return " ".join(reason_parts)

