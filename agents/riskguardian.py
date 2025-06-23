# agents/riskguardian.py

def evaluate_risk(symbol: str, volatility: float, sentiment: str) -> str:
    """
    Simple risk evaluation logic.
    """
    try:
        if volatility > 2.0 and sentiment == "bearish":
            return "high"
        elif volatility < 1.0 and sentiment == "bullish":
            return "low"
        else:
            return "medium"
    except Exception:
        return "unknown"
