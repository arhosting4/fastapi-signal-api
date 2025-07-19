def get_tier(confidence: float) -> str:
    """
    اعتماد کے اسکور کی بنیاد پر AI کا درجہ متعین کرتا ہے۔
    """
    if confidence >= 90:
        return "Tier 1 – Elite"
    elif confidence >= 80:
        return "Tier 2 – Strong"
    elif confidence >= 70:
        return "Tier 3 – Moderate"
    elif confidence >= 60:
        return "Tier 4 – Caution"
    else:
        return "Tier 5 – Weak"
