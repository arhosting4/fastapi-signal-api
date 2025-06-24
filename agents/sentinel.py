# src/agents/sentinel.py

def validate_signal(signal: str, risk_score: float, confidence: float) -> bool:
    """
    Validates signal based on basic sanity checks and thresholds.
    Returns True if signal is strong enough to act on.
    """
    if signal not in ["buy", "sell"]:
        return False
    if risk_score > 0.7:
        return False
    if confidence < 0.6:
        return False
    return True
