# agents/tierbot.py

def determine_tier(confidence: float, feedback: list, news_blocked: bool, risk_blocked: bool):
    if news_blocked:
        return "Blocked - Red news event"
    
    if risk_blocked:
        return "Blocked - High risk level"
    
    negatives = feedback.count("negative")
    positives = feedback.count("positive")

    score = confidence + (positives * 5) - (negatives * 10)

    if score >= 80:
        return "Tier 1"
    elif score >= 50:
        return "Tier 2"
    else:
        return "Blocked - Poor performance"
