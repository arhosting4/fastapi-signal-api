# agents/riskguardian.py

def evaluate_risk(closes: list, pattern: str, signal: str) -> str:
    """
    Evaluate risk level based on price action and detected patterns.
    Returns: "low", "medium", or "high"
    """

    if len(closes) < 10:
        return "high"  # not enough data is always high risk

    # Calculate volatility (simple)
    recent_range = max(closes[-5:]) - min(closes[-5:])
    avg_change = sum(abs(closes[i] - closes[i - 1]) for i in range(-5, 0)) / 4

    volatility = recent_range / avg_change if avg_change != 0 else 0

    # Risk based on volatility
    if volatility > 4:
        vol_risk = "high"
    elif volatility > 2:
        vol_risk = "medium"
    else:
        vol_risk = "low"

    # Risk based on pattern strength
    pattern_risk = {
        "three_white_soldiers": "low",
        "three_black_crows": "low",
        "bullish_engulfing": "medium",
        "bearish_engulfing": "medium",
        "doji": "high",
        "none": "medium",
        "error": "high"
    }.get(pattern, "medium")

    # Risk based on current signal direction
    signal_risk = {
        "buy": "medium",
        "sell": "medium",
        "wait": "low"
    }.get(signal, "high")

    # Combine all risk factors
    risk_score = sum([
        {"low": 1, "medium": 2, "high": 3}[vol_risk],
        {"low": 1, "medium": 2, "high": 3}[pattern_risk],
        {"low": 1, "medium": 2, "high": 3}[signal_risk],
    ])

    # Final risk classification
    if risk_score <= 4:
        return "low"
    elif risk_score <= 6:
        return "medium"
    else:
        return "high"
