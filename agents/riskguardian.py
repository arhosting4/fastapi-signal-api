# src/agents/riskguardian.py

def assess_risk(symbol: str, highs: list, lows: list, pattern: str) -> str:
    """
    Evaluates the dynamic market risk based on price spread, pattern strength, and chaos level.
    Returns: 'Low Risk', 'Moderate Risk', or 'High Risk'
    """
    if len(highs) < 5 or len(lows) < 5:
        return "Unknown Risk"

    spreads = [h - l for h, l in zip(highs[-5:], lows[-5:])]
    avg_spread = sum(spreads) / len(spreads)

    # Determine volatility level
    if avg_spread > 2.5:
        volatility = "High"
    elif avg_spread > 1.2:
        volatility = "Moderate"
    else:
        volatility = "Low"

    # Pattern reliability weighting
    strong_patterns = ["Bullish Engulfing", "Bearish Engulfing", "Upside Breakout", "Downside Breakout"]
    medium_patterns = ["Bullish Pin Bar", "Bearish Pin Bar"]
    weak_patterns = ["No pattern"]

    if pattern in strong_patterns:
        pattern_score = "Reliable"
    elif pattern in medium_patterns:
        pattern_score = "Cautious"
    else:
        pattern_score = "Unreliable"

    # Final risk logic
    if volatility == "High" or pattern_score == "Unreliable":
        return "High Risk"
    elif volatility == "Moderate" and pattern_score != "Reliable":
        return "Moderate Risk"
    else:
        return "Low Risk"
