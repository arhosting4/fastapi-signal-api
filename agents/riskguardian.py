# src/agents/riskguardian.py

def evaluate_risk(volatility: float, spread: float, news_impact: float) -> str:
    """
    Evaluates trading risk level.
    Returns: 'low', 'medium', or 'high'.
    """
    if news_impact > 7 or volatility > 6:
        return "high"
    elif spread > 2 or volatility > 3:
        return "medium"
    else:
        return "low"
