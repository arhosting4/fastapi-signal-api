import pandas as pd
import pandas_ta as ta # Import pandas_ta

def generate_core_signal(symbol: str, tf: str, closes: list) -> str:
    """
    Generates a core trading signal based on a simple strategy using pandas_ta.
    This version uses RSI (Relative Strength Index) and SMA (Simple Moving Average).
    """
    if len(closes) < 100: # Need enough data for indicators, e.g., RSI(14) needs at least 14 periods
        return "wait"

    # Convert closes list to a pandas Series
    close_series = pd.Series(closes)

    # Calculate RSI
    rsi = ta.rsi(close_series, length=14)

    # Calculate SMA
    sma_short = ta.sma(close_series, length=20)
    sma_long = ta.sma(close_series, length=50)

    # Get the latest values
    latest_rsi = rsi.iloc[-1]
    latest_close = close_series.iloc[-1] # Not directly used for signal, but good to have
    latest_sma_short = sma_short.iloc[-1]
    latest_sma_long = sma_long.iloc[-1]

    # Simple Strategy:
    # Buy if RSI is oversold (e.g., < 30) and short SMA crosses above long SMA
    # Sell if RSI is overbought (e.g., > 70) and short SMA crosses below long SMA

    if latest_rsi < 30 and latest_sma_short > latest_sma_long and sma_short.iloc[-2] <= sma_long.iloc[-2]:
        return "buy"
    elif latest_rsi > 70 and latest_sma_short < latest_sma_long and sma_short.iloc[-2] >= sma_long.iloc[-2]:
        return "sell"
    else:
        return "wait"

def fetch_ohlc(symbol: str, interval: str, data: list) -> dict:
    # This function is now redundant as real data is fetched by fetch_real_ohlc_data in app.py
    # and fusion_engine uses the full candle data.
    # However, if you still need a dummy OHLC for some reason, keep it.
    # Otherwise, you can remove this function if it's not called anywhere else.
    if len(data) < 5:
        return {}
    return {
        "open": data[-5],
        "high": max(data[-5:]),
        "low": min(data[-5:]),
        "close": data[-1],
        "volume": 1000
    }
