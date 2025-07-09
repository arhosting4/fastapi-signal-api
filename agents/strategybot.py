# src/agents/strategybot.py
import pandas_ta as ta
import pandas as pd
import numpy as np

def generate_core_signal(symbol: str, tf: str, closes: list) -> str:
    """
    Generates a core trading signal (buy/sell/wait) based on multiple
    technical indicators using pandas_ta.

    Parameters:
        symbol (str): The trading pair symbol.
        tf (str): Timeframe (e.g., 1min).
        closes (list): List of closing prices (oldest to newest).

    Returns:
        str: "buy", "sell", or "wait".
    """
    # Ensure we have enough data for indicators (e.g., 20 periods for many MAs)
    if len(closes) < 34: # Adjusted for indicators like MACD (26 periods) or BBands (20 periods)
        return "wait"

    # Convert closes list to a pandas Series for pandas_ta
    close_series = pd.Series(closes)

    # --- Indicator Calculations ---

    # SMA (Simple Moving Average) - Crossover Strategy
    # Short-term SMA (e.g., 10 periods) and Long-term SMA (e.g., 30 periods)
    sma_short = ta.sma(close_series, length=10)
    sma_long = ta.sma(close_series, length=30)

    # RSI (Relative Strength Index)
    # RSI values typically range from 0 to 100. Overbought > 70, Oversold < 30.
    rsi = ta.rsi(close_series, length=14)

    # MACD (Moving Average Convergence Divergence)
    # MACD Line, Signal Line, Histogram
    macd = ta.macd(close_series, fast=12, slow=26, signal=9)
        
    # --- DEBUGGING MACD COLUMNS ---
    print(f"DEBUG: MACD DataFrame columns: {macd.columns.tolist()}")
    # --- END DEBUGGING ---

    # Try to access MACD components using common naming conventions
    # Fallback to default if specific names are not found
    macd_line_col = f'MACD_{12}_{26}_{9}'
    macd_signal_col = f'MACDS_{12}_{26}_{9}'
    macd_hist_col = f'MACDH_{12}_{26}_{9}'

    # Check if columns exist, otherwise try alternative names or handle gracefully
    macd_line = macd[macd_line_col] if macd_line_col in macd.columns else None
    macd_signal = macd[macd_signal_col] if macd_signal_col in macd.columns else None
    macd_hist = macd[macd_hist_col] if macd_hist_col in macd.columns else None

    # If any MACD component is missing, return 'wait' or handle as an error
    if macd_line is None or macd_signal is None or macd_hist is None:
        print(f"DEBUG: Missing one or more MACD columns. Found: {macd.columns.tolist()}")
        return "wait" # Or raise an error if this is critical

    # Bollinger Bands (BBANDS)
    # Lower Band, Middle Band (SMA), Upper Band
    bbands = ta.bbands(close_series, length=20, std=2.0)
    bb_lower = bbands[f'BBL_{20}_{2.0}']
    bb_upper = bbands[f'BBU_{20}_{2.0}']
    bb_middle = bbands[f'BBM_{20}_{2.0}'] # This is the SMA(20)

    # --- Signal Generation Logic ---
    # Combine multiple indicators for a stronger signal

    buy_signals = 0
    sell_signals = 0

    # 1. SMA Crossover
    # Ensure values are not NaN before comparison
    if not sma_short.empty and not sma_long.empty and \
       not pd.isna(sma_short.iloc[-1]) and not pd.isna(sma_long.iloc[-1]) and \
       not pd.isna(sma_short.iloc[-2]) and not pd.isna(sma_long.iloc[-2]):
        if sma_short.iloc[-1] > sma_long.iloc[-1] and sma_short.iloc[-2] <= sma_long.iloc[-2]:
            buy_signals += 1 # Short SMA crosses above Long SMA (Golden Cross)
        elif sma_short.iloc[-1] < sma_long.iloc[-1] and sma_short.iloc[-2] >= sma_long.iloc[-2]:
            sell_signals += 1 # Short SMA crosses below Long SMA (Death Cross)

    # 2. RSI
    if not rsi.empty and not pd.isna(rsi.iloc[-1]):
        if rsi.iloc[-1] < 30: # Oversold
            buy_signals += 1
        elif rsi.iloc[-1] > 70: # Overbought
            sell_signals += 1

    # 3. MACD Crossover
    # Ensure values are not NaN before comparison
    if not macd_line.empty and not macd_signal.empty and \
       not pd.isna(macd_line.iloc[-1]) and not pd.isna(macd_signal.iloc[-1]) and \
       not pd.isna(macd_line.iloc[-2]) and not pd.isna(macd_signal.iloc[-2]):
        if macd_line.iloc[-1] > macd_signal.iloc[-1] and macd_line.iloc[-2] <= macd_signal.iloc[-2]:
            buy_signals += 1
        elif macd_line.iloc[-1] < macd_signal.iloc[-1] and macd_line.iloc[-2] >= macd_signal.iloc[-2]:
            sell_signals += 1
            
    # 4. Bollinger Bands
    # Ensure values are not NaN before comparison
    if not close_series.empty and not bb_lower.empty and not bb_upper.empty and \
       not pd.isna(close_series.iloc[-1]) and not pd.isna(bb_lower.iloc[-1]) and not pd.isna(bb_upper.iloc[-1]):
        if close_series.iloc[-1] < bb_lower.iloc[-1]: # Price below lower band
            buy_signals += 1
        elif close_series.iloc[-1] > bb_upper.iloc[-1]: # Price above upper band
            sell_signals += 1

    # --- Final Decision ---
    if buy_signals > sell_signals and buy_signals >= 2: # Require at least 2 buy signals
        return "buy"
    elif sell_signals > buy_signals and sell_signals >= 2: # Require at least 2 sell signals
        return "sell"
    else:
        return "wait"

                                     
