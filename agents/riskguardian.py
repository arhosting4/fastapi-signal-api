# src/agents/riskguardian.py

def evaluate_risk(symbol: str, candles: list) -> str:
    """
    Evaluates basic market risk using volatility between recent candles.
    """
    try:
        highs = [float(c["high"]) for c in candles]
        lows = [float(c["low"]) for c in candles]

        if len(highs) < 3 or len(lows) < 3:
            return "unknown"

        avg_range = sum([h - l for h, l in zip(highs, lows)]) / len(highs)

        if avg_range > 2.0:
            return "high"
        elif avg_range > 1.0:
            return "medium"
        else:
            return "low"
    except Exception:
        return "error"
