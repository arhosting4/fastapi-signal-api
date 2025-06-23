# src/agents/sentinel.py

def sentinel_guard(symbol: str, highs: list, lows: list, closes: list) -> dict:
    """
    Scans recent market data to detect unusual volatility, wick traps, or anomalies.
    Flags dangerous market structure for added AI safety.
    """

    if len(highs) < 5 or len(lows) < 5 or len(closes) < 5:
        return {
            "safe": False,
            "alert": "Insufficient data"
        }

    recent_range = max(highs[-5:]) - min(lows[-5:])
    last_close = closes[-1]
    avg_range = sum([h - l for h, l in zip(highs[-5:], lows[-5:])]) / 5

    # Volatility spike detection
    if recent_range > avg_range * 2.5:
        return {
            "safe": False,
            "alert": "🧨 High volatility spike detected"
        }

    # Wick trap detection
    last_candle_body = abs(closes[-1] - closes[-2])
    wick_top = highs[-1] - max(closes[-1], closes[-2])
    wick_bottom = min(closes[-1], closes[-2]) - lows[-1]

    if wick_top > last_candle_body * 2.5 or wick_bottom > last_candle_body * 2.5:
        return {
            "safe": False,
            "alert": "⚠️ Wick trap structure detected"
        }

    return {
        "safe": True,
        "alert": "✅ Market structure normal"
    }
