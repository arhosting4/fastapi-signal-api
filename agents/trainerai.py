# src/agents/trainerai.py
import random

def get_confidence(
    core_signal: str,
    pattern_signal_type: str, # bullish, bearish, neutral
    risk_status: str, # Normal, Moderate, High
    news_impact: str # Clear, Low, Medium, High
) -> float:
    """
    Estimates signal confidence based on current logic fusion.
    This version considers alignment of core strategy, pattern recognition,
    and market risk/news impact.

    Parameters:
        core_signal (str): Signal from core strategy logic ("buy", "sell", "wait").
        pattern_signal_type (str): Type of pattern detected ("bullish", "bearish", "neutral").
        risk_status (str): Risk assessment from riskguardian ("Normal", "Moderate", "High").
        news_impact (str): News impact assessment from sentinel ("Clear", "Low", "Medium", "High").

    Returns:
        float: Confidence percentage from 0% to 100%.
    """
    confidence = 50.0 # Base confidence

    # --- 1. Core Signal and Pattern Alignment ---
    # Reward alignment, penalize contradiction
    if core_signal == "buy" and pattern_signal_type == "bullish":
        confidence += 20
    elif core_signal == "sell" and pattern_signal_type == "bearish":
        confidence += 20
    elif core_signal == "wait" and pattern_signal_type == "neutral":
        confidence += 10
    elif (core_signal == "buy" and pattern_signal_type == "bearish") or \
         (core_signal == "sell" and pattern_signal_type == "bullish"):
        confidence -= 25 # Strong contradiction

    # --- 2. Risk Assessment Impact ---
    if risk_status == "High":
        confidence -= 20
    elif risk_status == "Moderate":
        confidence -= 10
    # "Normal" risk has no penalty

    # --- 3. News Impact Assessment ---
    if news_impact == "High":
        confidence -= 25
    elif news_impact == "Medium":
        confidence -= 15
    elif news_impact == "Low":
        confidence -= 5
    # "Clear" news has no penalty

    # --- 4. Additional Factors (can be expanded) ---
    # Example: If core signal is 'wait', confidence should generally be lower
    if core_signal == "wait":
        confidence -= 10 # Reduce confidence for neutral signals

    # Ensure confidence stays within 0-100 range
    confidence = max(0.0, min(100.0, confidence))

    # Add a small random variation to make it less predictable, but within bounds
    confidence += random.uniform(-2.0, 2.0)
    confidence = max(0.0, min(100.0, confidence))

    return round(confidence, 2)

