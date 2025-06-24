# src/agents/patternai.py

def detect_candle_pattern(open_price: float, high: float, low: float, close: float) -> str:
    """
    Detects simple candlestick pattern from OHLC values.
    Returns one of: 'bullish_engulfing', 'bearish_engulfing', 'doji', or 'none'.
    """
    body = abs(close - open_price)
    range_ = high - low

    if body < (0.1 * range_):
        return "doji"
    elif close > open_price and (open_price - low) < body and (high - close) < body:
        return "bullish_engulfing"
    elif open_price > close and (close - low) < body and (high - open_price) < body:
        return "bearish_engulfing"
    else:
        return "none"
