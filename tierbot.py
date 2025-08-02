# filename: tierbot.py

def get_tier(confidence: float, risk_status: str) -> str:
    """
    اعتماد (confidence) اور رسک (risk_status) کی بنیاد پر سگنل کا حتمی Tier طے کرے۔
    Output: "Tier 1 – Elite", "Tier 2 – Strong" ... "Tier 5 – Critical Risk" (واضح labeling، UI-ready)
    """
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
        
