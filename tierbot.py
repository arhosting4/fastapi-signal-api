# filename: tierbot.py

def get_tier(tech_score: float, confidence: float) -> str:
    """
    AI سگنل کی درجہ بندی کرتا ہے confidence اور tech_score کی بنیاد پر۔
    یہ درجہ بتاتا ہے کہ سگنل کتنا قابلِ اعتماد، مستحکم اور تجارتی لحاظ سے مضبوط ہے۔
    """

    if confidence >= 90 and tech_score >= 80:
        return "Tier 1 – Elite"
    elif confidence >= 80 and tech_score >= 70:
        return "Tier 2 – Strong"
    elif confidence >= 70 and tech_score >= 60:
        return "Tier 3 – Moderate"
    elif confidence >= 60 and tech_score >= 50:
        return "Tier 4 – Caution"
    else:
        return "Tier 5 – Weak"
