# src/agents/sentinel.py

def validate_signal(signal: str, risk: str, tier: str) -> bool:
    """
    Validates the signal based on AI risk and tier evaluations.
    Returns True if it's safe to proceed, otherwise False.
    """
    if signal == "wait":
        return False

    if risk == "high" and tier == "C":
        return False

    if signal in ["buy", "sell"] and risk in ["low", "medium"] and tier in ["A", "B"]:
        return True

    return False
