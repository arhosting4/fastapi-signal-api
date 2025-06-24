# src/agents/patternai.py

def detect_candle_pattern(data: list) -> str:
    """
    Detects candlestick patterns from the recent OHLC data.
    Returns either 'bullish', 'bearish', or 'neutral'.
    
    `data` is a list of candle dictionaries with keys: open, high, low, close.
    """

    if len(data) < 2:
        return "neutral"  # not enough data

    last_candle = data[-1]
    prev_candle = data[-2]

    # Basic bullish engulfing
    if (
        prev_candle["close"] < prev_candle["open"]
        and last_candle["close"] > last_candle["open"]
        and last_candle["close"] > prev_candle["open"]
        and last_candle["open"] < prev_candle["close"]
    ):
        return "bullish"

    # Basic bearish engulfing
    if (
        prev_candle["close"] > prev_candle["open"]
        and last_candle["close"] < last_candle["open"]
        and last_candle["open"] > prev_candle["close"]
        and last_candle["close"] < prev_candle["open"]
    ):
        return "bearish"

    return "neutral"
