# src/agents/reasonbot.py

def analyze_candle_reasoning(symbol: str, tf: str, closes: list, opens: list, highs: list, lows: list) -> str:
    """
    Analyzes candle patterns and market structure to add deeper reasoning for signal generation.
    Returns a string reason.
    """
    if len(closes) < 5 or len(opens) < 5:
        return "Insufficient data for reasoning"

    recent_candle = closes[-1] - opens[-1]
    previous_candle = closes[-2] - opens[-2]

    is_bullish = recent_candle > 0
    is_bearish = recent_candle < 0

    avg_body_size = sum([abs(c - o) for c, o in zip(closes[-5:], opens[-5:])]) / 5
    current_body_size = abs(recent_candle)

    # Trend & momentum logic
    trend_up = all(closes[i] > closes[i - 1] for i in range(-4, 0))
    trend_down = all(closes[i] < closes[i - 1] for i in range(-4, 0))

    if is_bullish and current_body_size > avg_body_size * 1.2 and trend_up:
        return "Strong bullish candle breakout with upward momentum"
    elif is_bearish and current_body_size > avg_body_size * 1.2 and trend_down:
        return "Strong bearish candle breakout with downward momentum"
    elif is_bullish and not trend_up:
        return "Bullish candle but no clear trend confirmation"
    elif is_bearish and not trend_down:
        return "Bearish candle but no clear trend confirmation"
    else:
        return "Sideways or indecisive market structure"

def get_market_bias(symbol: str, closes: list) -> str:
    """
    Determines overall market bias based on recent price structure.
    """
    if len(closes) < 5:
        return "neutral"

    last = closes[-1]
    prev = closes[-2]
    earlier = closes[-3]

    if last > prev > earlier:
        return "bullish"
    elif last < prev < earlier:
        return "bearish"
    else:
        return "neutral"
