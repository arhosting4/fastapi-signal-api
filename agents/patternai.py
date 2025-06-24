# src/agents/patternai.py

def detect_pattern(symbol: str, candles: list) -> str:
    """
    Detects basic bullish or bearish patterns from recent candles.
    """
    try:
        closes = [float(c["close"]) for c in candles]

        if len(closes) < 3:
            return "insufficient data"

        if closes[-1] > closes[-2] > closes[-3]:
            return "bullish"
        elif closes[-1] < closes[-2] < closes[-3]:
            return "bearish"
        else:
            return "sideways"
    except Exception:
        return "pattern detection error"
