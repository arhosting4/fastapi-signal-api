import pandas as pd
import pandas_ta as ta

def calculate_tp_sl(candles: list, atr_multiplier: float = 2.0):
    if not candles or len(candles) < 14:
        return None
    
    df = pd.DataFrame(candles)
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])
    
    atr = ta.atr(df['high'], df['low'], df['close'], length=14)
    if atr is None or atr.empty or pd.isna(atr.iloc[-1]):
        return None
        
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

    df = pd.DataFrame(candles)
    close_series = pd.to_numeric(df['close'])
    high_series = pd.to_numeric(df['high'])
    low_series = pd.to_numeric(df['low'])

    sma_short = ta.sma(close_series, length=10)
    sma_long = ta.sma(close_series, length=30)
    rsi = ta.rsi(close_series, length=14)
    macd_data = ta.macd(close_series, fast=12, slow=26, signal=9)
    bbands_data = ta.bbands(close_series, length=20, std=2.0)
    stoch_data = ta.stoch(high=high_series, low=low_series, close=close_series, k=14, d=3, smooth_k=3)
    
    if any(s is None or s.empty for s in [sma_short, sma_long, rsi, macd_data, bbands_data, stoch_data]):
        return {"signal": "wait"}

    stoch_k = stoch_data.iloc[:, 0]
    macd_line = macd_data.iloc[:, 0]
    macd_signal = macd_data.iloc[:, 1]
    bb_lower = bbands_data.iloc[:, 0]
    bb_upper = bbands_data.iloc[:, 2]

    buy_signals = 0
    sell_signals = 0

    if sma_short.iloc[-1] > sma_long.iloc[-1] and sma_short.iloc[-2] <= sma_long.iloc[-2]: buy_signals += 1
    if sma_short.iloc[-1] < sma_long.iloc[-1] and sma_short.iloc[-2] >= sma_long.iloc[-2]: sell_signals += 1
    if rsi.iloc[-1] < 30: buy_signals += 1
    if rsi.iloc[-1] > 70: sell_signals += 1
    if macd_line.iloc[-1] > macd_signal.iloc[-1] and macd_line.iloc[-2] <= macd_signal.iloc[-2]: buy_signals += 1
    if macd_line.iloc[-1] < macd_signal.iloc[-1] and macd_line.iloc[-2] >= macd_signal.iloc[-2]: sell_signals += 1
    if close_series.iloc[-1] < bb_lower.iloc[-1]: buy_signals += 1
    if close_series.iloc[-1] > bb_upper.iloc[-1]: sell_signals += 1
    if stoch_k.iloc[-1] < 20: buy_signals += 1
    if stoch_k.iloc[-1] > 80: sell_signals += 1

    signal = "wait"
    if buy_signals > sell_signals:
        signal = "buy"
    elif sell_signals > buy_signals:
        signal = "sell"
    elif macd_line.iloc[-1] > macd_signal.iloc[-1]:
        signal = "buy"
    else:
        signal = "sell"
            
    return {"signal": signal}
                
