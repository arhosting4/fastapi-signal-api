# filename: tierbot.py
def get_tier(confidence: float, risk_status: str) -> str:
    """اعتماد اور رسک کی بنیاد پر AI کا درجہ متعین کرتا ہے۔"""
    if risk_status == "Critical":
        return "Tier 5 – Critical Risk"
    
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
