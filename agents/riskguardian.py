# src/agents/riskguardian.py

def evaluate_risk(symbol: str, closes: list, highs: list, lows: list, confidence: float, bias: str) -> str:
    """
    Evaluates signal risk level based on price volatility and AI confidence.
    """
    if len(closes) < 5 or len(highs) < 5 or len(lows) < 5:
        return "unknown"

    recent_range = [h - l for h, l in zip(highs[-5:], lows[-5:])]
    avg_range = sum(recent_range) / len(recent_range)
    last_range = highs[-1] - lows[-1]

    volatility_ratio = last_range / avg_range if avg_range != 0 else 1
    bias_multiplier = 1.5 if bias == "neutral" else 1.0

    # Risk score calculation
    risk_score = (volatility_ratio * bias_multiplier) - confidence

    if risk_score > 1.2:
        return "high"
    elif risk_score > 0.5:
        return "medium"
    else:
        return "low"
