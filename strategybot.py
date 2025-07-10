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
    # MACD needs at least 26 periods, Bollinger Bands 20, SMA 30.
    # Let's ensure we have enough data for the longest period (30 for SMA_long) plus a few for lookback.
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
        
    # Corrected MACD column names based on debug logs
    # Ensure MACD columns exist before accessing
    macd_line = macd[f'MACD_12_26_9'] if f'MACD_12_26_9' in macd else pd.Series()
    macd_signal = macd[f'MACDs_12_26_9'] if f'MACDs_12_26_9' in macd else pd.Series()
    macd_hist = macd[f'MACDh_12_26_9'] if f'MACDh_12_26_9' in macd else pd.Series()

    # Bollinger Bands (BBANDS)
    # Lower Band, Middle Band (SMA), Upper Band
    bbands = ta.bbands(close_series, length=20, std=2.0)
    bb_lower = bbands[f'BBL_20_2.0'] if f'BBL_20_2.0' in bbands else pd.Series()
    bb_upper = bbands[f'BBU_20_2.0'] if f'BBU_20_2.0' in bbands else pd.Series()
    bb_middle = bbands[f'BBM_20_2.0'] if f'BBM_20_2.0' in bbands else pd.Series() # This is the SMA(20)

    # --- Signal Generation Logic ---
    # Combine multiple indicators for a stronger signal

    buy_signals = 0
    sell_signals = 0

    # Helper function to safely get the last valid value from a Series
    def get_last_valid(series):
        if not series.empty and not series.isnull().all():
            return series.iloc[-1]
        return np.nan # Return NaN if series is empty or all NaNs

    def get_second_last_valid(series):
        if len(series) >= 2 and not series.iloc[-2:].isnull().all():
            # Find the last non-NaN value from the last two elements
            if not pd.isna(series.iloc[-1]):
                if not pd.isna(series.iloc[-2]):
                    return series.iloc[-2]
                else: # If last is valid, but second last is NaN, try to find earlier valid
                    for i in range(len(series) - 2, -1, -1):
                        if not pd.isna(series.iloc[i]):
                            return series.iloc[i]
            else: # If last is NaN, try to find the last valid one
                for i in range(len(series) - 1, -1, -1):
                    if not pd.isna(series.iloc[i]):
                        return series.iloc[i]
        return np.nan


    # 1. SMA Crossover
    # Ensure values are not NaN before comparison
    sma_short_last = get_last_valid(sma_short)
    sma_long_last = get_last_valid(sma_long)
    sma_short_prev = get_second_last_valid(sma_short)
    sma_long_prev = get_second_last_valid(sma_long)

    if not pd.isna(sma_short_last) and not pd.isna(sma_long_last) and \
       not pd.isna(sma_short_prev) and not pd.isna(sma_long_prev):
        if sma_short_last > sma_long_last and sma_short_prev <= sma_long_prev:
            buy_signals += 1 # Short SMA crosses above Long SMA (Golden Cross)
        elif sma_short_last < sma_long_last and sma_short_prev >= sma_long_prev:
            sell_signals += 1 # Short SMA crosses below Long SMA (Death Cross)

    # 2. RSI
    rsi_last = get_last_valid(rsi)
    if not pd.isna(rsi_last):
        if rsi_last < 30: # Oversold
            buy_signals += 1
        elif rsi_last > 70: # Overbought
            sell_signals += 1

    # 3. MACD Crossover
    macd_line_last = get_last_valid(macd_line)
    macd_signal_last = get_last_valid(macd_signal)
    macd_line_prev = get_second_last_valid(macd_line)
    macd_signal_prev = get_second_last_valid(macd_signal)

    if not pd.isna(macd_line_last) and not pd.isna(macd_signal_last) and \
       not pd.isna(macd_line_prev) and not pd.isna(macd_signal_prev):
        if macd_line_last > macd_signal_last and macd_line_prev <= macd_signal_prev:
            buy_signals += 1
        elif macd_line_last < macd_signal_last and macd_line_prev >= macd_signal_prev:
            sell_signals += 1
            
    # 4. Bollinger Bands
    close_last = get_last_valid(close_series)
    bb_lower_last = get_last_valid(bb_lower)
    bb_upper_last = get_last_valid(bb_upper)

    if not pd.isna(close_last) and not pd.isna(bb_lower_last) and not pd.isna(bb_upper_last):
        if close_last < bb_lower_last: # Price below lower band
            buy_signals += 1
        elif close_last > bb_upper_last: # Price above upper band
            sell_signals += 1

    # --- Final Decision ---
    if buy_signals > sell_signals and buy_signals >= 2: # Require at least 2 buy signals
        return "buy"
    elif sell_signals > buy_signals and sell_signals >= 2: # Require at least 2 sell signals
        return "sell"
    else:
        return "wait"


def calculate_tp_sl(signal: str, current_price: float, high_prices: list, low_prices: list) -> dict:
    """
    Calculates Take Profit (TP) and Stop Loss (SL) levels based on ATR.

    Parameters:
        signal (str): The trading signal ("buy", "sell", "wait").
        current_price (float): The current closing price.
        high_prices (list): List of high prices (oldest to newest).
        low_prices (list): List of low prices (oldest to newest).

    Returns:
        dict: Dictionary containing 'tp' and 'sl' levels, or None if not applicable.
    """
    if signal == "wait" or len(high_prices) < 14 or len(low_prices) < 14: # ATR needs at least 14 periods
        return {"tp": None, "sl": None}

    # Create pandas Series for high, low, and close (current_price is the last close)
    # We need a series for close to calculate ATR
    close_series_for_atr = pd.Series(high_prices) # Just using high_prices as a base for length, will replace last value
    close_series_for_atr.iloc[-1] = current_price # Ensure the last value is the current price

    # Calculate ATR
    atr = ta.atr(pd.Series(high_prices), pd.Series(low_prices), close_series_for_atr, length=14)
    
    if atr.empty or pd.isna(atr.iloc[-1]):
        return {"tp": None, "sl": None}

    current_atr = atr.iloc[-1]

    # ATR Multipliers (can be tuned)
    # Common practice: 1.5 to 2.0 times ATR for SL, 2.0 to 3.0 times ATR for TP
    sl_multiplier = 1.5
    tp_multiplier = 2.5

    tp = None
    sl = None

    if signal == "buy":
        tp = current_price + (current_atr * tp_multiplier)
        sl = current_price - (current_atr * sl_multiplier)
    elif signal == "sell":
        tp = current_price - (current_atr * tp_multiplier)
        sl = current_price + (current_atr * sl_multiplier)
    
    # Round to a reasonable number of decimal places for currency pairs (e.g., 4 or 5)
    # You might need to adjust this based on the specific symbol (e.g., crypto needs more decimals)
    if tp is not None:
        tp = round(tp, 5)
    if sl is not None:
        sl = round(sl, 5)

    return {"tp": tp, "sl": sl}
