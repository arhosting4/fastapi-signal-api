import pandas as pd
import pandas_ta as ta

def generate_core_signal(symbol: str, tf: str, closes: list) -> str:
    """
    Generates a core trading signal based on a more advanced strategy using pandas_ta.
    This version combines RSI, MACD, and Bollinger Bands for confirmation.
    """
    # Need enough data for indicators:
    # RSI(14) needs 14 periods
    # MACD(12, 26, 9) needs at least 26 periods
    # Bollinger Bands (20) needs 20 periods
    # Let's ensure we have at least 100 periods for robust calculation
    if len(closes) < 100:
        return "wait"

    # Convert closes list to a pandas Series
    close_series = pd.Series(closes)

    # Calculate Indicators
    # RSI (Relative Strength Index)
    rsi = ta.rsi(close_series, length=14)

    # MACD (Moving Average Convergence Divergence)
    # Default: fast=12, slow=26, signal=9
    macd = ta.macd(close_series, fast=12, slow=26, signal=9)
    macd_line = macd[macd.columns[0]] # MACD line
    signal_line = macd[macd.columns[1]] # Signal line

    # Bollinger Bands
    # Default: length=20, std=2
    bbands = ta.bbands(close_series, length=20, std=2)
    bb_lower = bbands[bbands.columns[0]] # Lower Band
    bb_middle = bbands[bbands.columns[1]] # Middle Band (SMA)
    bb_upper = bbands[bbands.columns[2]] # Upper Band

    # Get the latest values
    latest_rsi = rsi.iloc[-1]
    latest_macd_line = macd_line.iloc[-1]
    latest_signal_line = signal_line.iloc[-1]
    latest_close = close_series.iloc[-1]
    latest_bb_lower = bb_lower.iloc[-1]
    latest_bb_upper = bb_upper.iloc[-1]

    # Get previous values for crosses
    prev_macd_line = macd_line.iloc[-2]
    prev_signal_line = signal_line.iloc[-2]

    # --- Trading Strategy Logic ---

    # Buy Conditions:
    # 1. RSI is not overbought (e.g., < 70)
    # 2. MACD line crosses above Signal line (bullish crossover)
    # 3. Price is near or below Bollinger Lower Band (potential reversal from oversold)
    buy_condition_rsi = latest_rsi < 70
    buy_condition_macd = (latest_macd_line > latest_signal_line) and (prev_macd_line <= prev_signal_line)
    buy_condition_bb = latest_close <= latest_bb_lower # Price touches or goes below lower band

    if buy_condition_rsi and buy_condition_macd and buy_condition_bb:
        return "buy"

    # Sell Conditions:
    # 1. RSI is not oversold (e.g., > 30)
    # 2. MACD line crosses below Signal line (bearish crossover)
    # 3. Price is near or above Bollinger Upper Band (potential reversal from overbought)
    sell_condition_rsi = latest_rsi > 30
    sell_condition_macd = (latest_macd_line < latest_signal_line) and (prev_macd_line >= prev_signal_line)
    sell_condition_bb = latest_close >= latest_bb_upper # Price touches or goes above upper band

    if sell_condition_rsi and sell_condition_macd and sell_condition_bb:
        return "sell"

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
    
