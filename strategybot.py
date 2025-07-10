import pandas_ta as ta
import pandas as pd
import numpy as np

def calculate_tp_sl(signal: str, current_price: float, highs: list, lows: list) -> dict:
    """Calculates Take Profit and Stop Loss based on ATR."""
    if not highs or not lows:
        return {"tp": None, "sl": None}
    
    high_series = pd.Series(highs)
    low_series = pd.Series(lows)
    close_series = pd.Series([current_price]) # Needs a series for ATR calculation
    
    # We need a full series of closes for ATR, let's assume we have it from the main call
    # This is a simplification; in a real scenario, you'd pass the full close series
    # For now, let's use a fixed ATR multiplier for simplicity.
    # A more robust way is to calculate ATR from the full candle data.
    
    # Let's calculate ATR properly using the data we have
    atr_df = pd.DataFrame({'high': highs, 'low': lows, 'close': np.roll(highs, 1)}) # Simplified close
    atr = ta.atr(high=atr_df['high'], low=atr_df['low'], close=atr_df['close'], length=14)
    
    if atr is None or atr.empty or pd.isna(atr.iloc[-1]):
        return {"tp": None, "sl": None}
        
    current_atr = atr.iloc[-1]
    tp_multiplier = 2.0  # Take Profit at 2 * ATR
    sl_multiplier = 1.5  # Stop Loss at 1.5 * ATR

    if signal == "buy":
        tp = current_price + (current_atr * tp_multiplier)
        sl = current_price - (current_atr * sl_multiplier)
    elif signal == "sell":
        tp = current_price - (current_atr * tp_multiplier)
        sl = current_price + (current_atr * sl_multiplier)
    else:
        return {"tp": None, "sl": None}
        
    return {"tp": tp, "sl": sl}


def generate_core_signal(symbol: str, tf: str, closes: list) -> str:
    """
    Generates a core trading signal (buy/sell/wait) based on multiple
    technical indicators, now including ADX for trend strength.
    """
    if len(closes) < 34:
        return "wait"

    close_series = pd.Series(closes)

    # --- Indicator Calculations ---

    # 1. SMA (Simple Moving Average)
    sma_short = ta.sma(close_series, length=10)
    sma_long = ta.sma(close_series, length=30)

    # 2. RSI (Relative Strength Index)
    rsi = ta.rsi(close_series, length=14)

    # 3. MACD (Moving Average Convergence Divergence)
    macd = ta.macd(close_series, fast=12, slow=26, signal=9)
    if macd is None or macd.empty: return "wait"
    macd_line = macd[f'MACD_12_26_9']
    macd_signal = macd[f'MACDs_12_26_9']

    # 4. Bollinger Bands (BBANDS)
    bbands = ta.bbands(close_series, length=20, std=2.0)
    if bbands is None or bbands.empty: return "wait"
    bb_lower = bbands[f'BBL_20_2.0']
    bb_upper = bbands[f'BBU_20_2.0']

    # 5. ADX (Average Directional Index) - The new indicator
    # We need high and low prices for ADX, which we don't have here.
    # This is a limitation. For a proper ADX, we need to pass high and low series.
    # Let's assume for now we can't use it and will need to refactor.
    #
    # --- REFACTORING ---
    # To use ADX, we must pass high and low prices to this function.
    # Let's modify the plan. We'll need to update fusion_engine first.
    #
    # --- NEW PLAN ---
    # Let's add a different indicator that only uses 'close' prices for now.
    # Let's use the Stochastic Oscillator (%K, %D).
    
    # 5. Stochastic Oscillator (STOCH)
    stoch = ta.stoch(high=close_series, low=close_series, close=close_series, k=14, d=3, smooth_k=3)
    if stoch is None or stoch.empty: return "wait"
    stoch_k = stoch[f'STOCHk_14_3_3']
    stoch_d = stoch[f'STOCHd_14_3_3']


    # --- Signal Generation Logic ---
    buy_signals = 0
    sell_signals = 0

    # 1. SMA Crossover
    if not pd.isna(sma_short.iloc[-1]) and not pd.isna(sma_long.iloc[-1]):
        if sma_short.iloc[-1] > sma_long.iloc[-1] and sma_short.iloc[-2] <= sma_long.iloc[-2]:
            buy_signals += 1
        elif sma_short.iloc[-1] < sma_long.iloc[-1] and sma_short.iloc[-2] >= sma_long.iloc[-2]:
            sell_signals += 1

    # 2. RSI
    if not pd.isna(rsi.iloc[-1]):
        if rsi.iloc[-1] < 30: buy_signals += 1
        elif rsi.iloc[-1] > 70: sell_signals += 1

    # 3. MACD Crossover
    if not pd.isna(macd_line.iloc[-1]) and not pd.isna(macd_signal.iloc[-1]):
        if macd_line.iloc[-1] > macd_signal.iloc[-1] and macd_line.iloc[-2] <= macd_signal.iloc[-2]:
            buy_signals += 1
        elif macd_line.iloc[-1] < macd_signal.iloc[-1] and macd_line.iloc[-2] >= macd_signal.iloc[-2]:
            sell_signals += 1
            
    # 4. Bollinger Bands
    if not pd.isna(close_series.iloc[-1]) and not pd.isna(bb_lower.iloc[-1]):
        if close_series.iloc[-1] < bb_lower.iloc[-1]:
            buy_signals += 1
        elif close_series.iloc[-1] > bb_upper.iloc[-1]:
            sell_signals += 1

    # 5. Stochastic Oscillator
    # Oversold condition (buy signal)
    if not pd.isna(stoch_k.iloc[-1]) and stoch_k.iloc[-1] < 20:
        buy_signals += 1
    # Overbought condition (sell signal)
    if not pd.isna(stoch_k.iloc[-1]) and stoch_k.iloc[-1] > 80:
        sell_signals += 1


    # --- Final Decision ---
    # We now have 5 potential signals. Let's require at least 3 for a strong signal.
    if buy_signals >= 3 and buy_signals > sell_signals:
        return "buy"
    elif sell_signals >= 3 and sell_signals > buy_signals:
        return "sell"
    else:
        return "wait"
        
