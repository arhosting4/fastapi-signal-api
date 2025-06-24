# src/agents/reasonbot.py

def assess_context(signal: str, candle_pattern: str, risk_level: str, validation_status: bool) -> str:
    """
    Generates a reasoning string based on signal components.
    """

    reasons = []

    if signal in ["buy", "sell"]:
        reasons.append(f"Signal strength: {signal.upper()}")

    if candle_pattern != "none":
        reasons.append(f"Pattern: {candle_pattern}")

    reasons.append(f"Risk: {risk_level.upper()}")

    reasons.append("Validation: ✅" if validation_status else "Validation: ❌")

    return " | ".join(reasons)
