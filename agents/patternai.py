# src/agents/patternai.py

def detect_pattern(symbol: str, opens: list, closes: list, highs: list, lows: list) -> str:
    """
    Detects basic yet high-probability candlestick patterns.
    Extendable for more complex AI-based future patterns.
    """
    if len(opens) < 3 or len(closes) < 3:
        return "No pattern"

    o1, o2, o3 = opens[-3:]
    c1, c2, c3 = closes[-3:]
    h1, h2, h3 = highs[-3:]
    l1, l2, l3 = lows[-3:]

    # Bullish engulfing
    if c2 < o2 and c3 > o3 and c3 > o2 and o3 < c2:
        return "Bullish Engulfing"

    # Bearish engulfing
    if c2 > o2 and c3 < o3 and c3 < o2 and o3 > c2:
        return "Bearish Engulfing"

    # Pin bar (long wick reversal)
    body = abs(c3 - o3)
    wick_top = h3 - max(c3, o3)
    wick_bottom = min(c3, o3) - l3

    if wick_bottom > body * 2 and wick_top < body:
        return "Bullish Pin Bar"
    elif wick_top > body * 2 and wick_bottom < body:
        return "Bearish Pin Bar"

    # Breakout check
    recent_high = max(highs[-5:])
    recent_low = min(lows[-5:])

    if closes[-1] > recent_high * 0.995:
        return "Upside Breakout"
    elif closes[-1] < recent_low * 1.005:
        return "Downside Breakout"

    return "No pattern"
