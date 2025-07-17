import pandas_ta as ta
import pandas as pd
import numpy as np

def calculate_tp_sl(candles: list, atr_multiplier: float = 2.0):
    # ... (یہ فنکشن ویسے ہی رہے گا) ...
    if not candles or len(candles) < 14:
        return None, None
    df = pd.DataFrame(candles)
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])
    atr = ta.atr(df['high'], df['low'], df['close'], length=14)
    if atr is None or atr.empty or pd.isna(atr.iloc[-1]):
        return None, None
    last_atr = atr.iloc[-1]
    last_close = df['close'].iloc[-1]
    tp_buy = last_close + (last_atr * atr_multiplier)
    sl_buy = last_close - last_atr
    tp_sell = last_close - (last_atr * atr_multiplier)
    sl_sell = last_close + last_atr
    return (tp_buy, sl_buy), (tp_sell, sl_sell)

def generate_core_signal(symbol: str, tf: str, candles: list):
    if len(candles) < 34:
        return {"signal": "wait"}

    closes = [c['close'] for c in candles]
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    
    close_series = pd.Series(closes)
    high_series = pd.Series(highs)
    low_series = pd.Series(lows)

    # --- Indicator Calculations ---
    sma_short = ta.sma(close_series, length=10)
    sma_long = ta.sma(close_series, length=30)
    rsi = ta.rsi(close_series, length=14)
    macd_data = ta.macd(close_series, fast=12, slow=26, signal=9)
    bbands_data = ta.bbands(close_series, length=20, std=2.0)
    stoch_data = ta.stoch(high=high_series, low=low_series, close=close_series, k=14, d=3, smooth_k=3)
    
    stoch_k = stoch_data.iloc[:, 0] if stoch_data is not None and not stoch_data.empty else None
    macd_line = macd_data.iloc[:, 0] if macd_data is not None and not macd_data.empty else None
    macd_signal = macd_data.iloc[:, 1] if macd_data is not None and not macd_data.empty else None

    buy_signals = 0
    sell_signals = 0

    # ... (تمام سگنل کی منطق ویسی ہی رہے گی) ...
    if sma_short is not None and sma_long is not None and not sma_short.empty and not sma_long.empty:
        if sma_short.iloc[-1] > sma_long.iloc[-1] and sma_short.iloc[-2] <= sma_long.iloc[-2]:
            buy_signals += 1
        elif sma_short.iloc[-1] < sma_long.iloc[-1] and sma_short.iloc[-2] >= sma_long.iloc[-2]:
            sell_signals += 1
    if rsi is not None and not rsi.empty:
        if rsi.iloc[-1] < 30:
            buy_signals += 1
        elif rsi.iloc[-1] > 70:
            sell_signals += 1
    if macd_line is not None and macd_signal is not None:
        if macd_line.iloc[-1] > macd_signal.iloc[-1] and macd_line.iloc[-2] <= macd_signal.iloc[-2]:
            buy_signals += 1
        elif macd_line.iloc[-1] < macd_signal.iloc[-1] and macd_line.iloc[-2] >= macd_signal.iloc[-2]:
            sell_signals += 1
    if bbands_data is not None and not bbands_data.empty:
        bb_lower = bbands_data.iloc[:, 0]
        bb_upper = bbands_data.iloc[:, 2]
        if close_series.iloc[-1] < bb_lower.iloc[-1]:
            buy_signals += 1
        elif close_series.iloc[-1] > bb_upper.iloc[-1]:
            sell_signals += 1
    if stoch_k is not None and not stoch_k.empty:
        if stoch_k.iloc[-1] < 20:
            buy_signals += 1
        elif stoch_k.iloc[-1] > 80:
            sell_signals += 1

    # --- حتمی فیصلہ سازی کی منطق ---
    signal = "wait"
    if buy_signals > sell_signals:
        signal = "buy"
    elif sell_signals > buy_signals:
        signal = "sell"
    # --- اہم ترین تبدیلی: ٹائی بریکر منطق ---
    elif macd_line is not None and macd_signal is not None:
        # اگر سگنل برابر ہیں، تو MACD کے رجحان کو دیکھو
        if macd_line.iloc[-1] > macd_signal.iloc[-1]:
            signal = "buy" # MACD مثبت رجحان دکھا رہا ہے
        else:
            signal = "sell" # MACD منفی رجحان دکھا رہا ہے
            
    return {"signal": signal}
        
