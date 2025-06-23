# src/agents/sentinel.py

def validate_signal(signal: str, trend: str, tier: str) -> bool:
    """
    Validates signal consistency using tier and trend confirmation.
    Returns True if all parameters agree, otherwise False.
    """
    if signal == "buy" and trend == "uptrend" and tier in ["A", "B"]:
        return True
    elif signal == "sell" and trend == "downtrend" and tier in ["A", "B"]:
        return True
    elif signal == "wait":
        return True  # always valid
    return False
