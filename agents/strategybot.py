# src/agents/strategybot.py
import numpy as np
import pandas as pd
import pandas_ta as ta

def generate_core_signal(symbol: str, tf: str, candles: list) -> str:
    """
    Generates a core trading signal using multiple technical indicators:
    SMA Crossover, RSI, and MACD (using pandas_ta).

    Parameters:
        symbol (str): The trading pair symbol.
        tf (str): The timeframe.
        candles (list): A list of OHLCV candle dictionaries (oldest to newest).

    Returns:
        str: "buy", "sell", or "wait".
    """
    if len(candles) < 34: # Minimum data needed for MACD (26 + 9 for signal line)
        return "wait"

    # Convert candles to a Pandas DataFrame for pandas_ta
    df = pd.DataFrame(candles)
    df['open'] = pd.to_numeric(df['open'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])
    df['volume'] = pd.to_numeric(df['volume'])

    # --- 1. SMA Crossover Strategy (e.g., 10-period SMA vs 30-period SMA) ---
    df.ta.sma(length=10, append=True)
    df.ta.sma(length=30, append=True)

    sma_short = df[f'SMA_10']
    sma_long = df[f'SMA_30']

    sma_signal = "wait"
    if len(sma_short) >= 2 and len(sma_long) >= 2:
        if sma_short.iloc[-1] > sma_long.iloc[-1] and sma_short.iloc[-2] <= sma_long.iloc[-2]:
            sma_signal = "buy" # Bullish crossover
        elif sma_short.iloc[-1] < sma_long.iloc[-1] and sma_short.iloc[-2] >= sma_long.iloc[-2]:
            sma_signal = "sell" # Bearish crossover

    # --- 2. RSI (Relative Strength Index) Strategy ---
    df.ta.rsi(length=14, append=True)
    rsi = df['RSI_14']

    rsi_signal = "wait"
    if len(rsi) > 0:
        if rsi.iloc[-1] < 30:
            rsi_signal = "buy" # Oversold, potential buy
        elif rsi.iloc[-1] > 70:
            rsi_signal = "sell" # Overbought, potential sell

    # --- 3. MACD (Moving Average Convergence Divergence) Strategy ---
    df.ta.macd(fast=12, slow=26, signal=9, append=True)
    macd = df['MACD_12_26_9']
    macdsignal = df['MACDs_12_26_9']

    macd_signal = "wait"
    if len(macd) >= 2 and len(macdsignal) >= 2:
        if macd.iloc[-1] > macdsignal.iloc[-1] and macd.iloc[-2] <= macdsignal.iloc[-2]:
            macd_signal = "buy"
        elif macd.iloc[-1] < macdsignal.iloc[-1] and macd.iloc[-2] >= macdsignal.iloc[-2]:
            macd_signal = "sell"

    # --- Combine Signals (Simple Voting Mechanism) ---
    buy_votes = 0
    sell_votes = 0

    if sma_signal == "buy":
        buy_votes += 1
    elif sma_signal == "sell":
        sell_votes += 1

    if rsi_signal == "buy":
        buy_votes += 1
    elif rsi_signal == "sell":
        sell_votes += 1

    if macd_signal == "buy":
        buy_votes += 1
    elif macd_signal == "sell":
        sell_votes += 1

    # Decision Logic
    if buy_votes >= 2: # At least two indicators suggest buy
        return "buy"
    elif sell_votes >= 2: # At least two indicators suggest sell
        return "sell"
    else:
        return "wait"

# The fetch_ohlc function is no longer needed as data is passed directly from app.py
# You can remove it or keep it as a placeholder.
def fetch_ohlc(symbol: str, interval: str, data: list) -> dict:
    """
    This function is now redundant as real OHLC data is fetched in app.py.
    It's kept for compatibility but will not be actively used for real data.
    """
    if len(data) < 5:
        return {}
    return {
        "open": data[-5],
        "high": max(data[-5:]),
        "low": min(data[-5:]),
        "close": data[-1],
        "volume": 1000
        }
    
