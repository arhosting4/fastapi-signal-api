# filename: strategybot.py
import pandas as pd
import pandas_ta as ta
from typing import List, Tuple, Optional, Dict

import config
from schemas import Candle

def calculate_tp_sl(candles: List[Candle], atr_multiplier: float) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]:
    if len(candles) < config.ATR_LENGTH:
        return None
    
    df = pd.DataFrame([c.dict() for c in candles])
    
    atr = ta.atr(df['high'], df['low'], df['close'], length=config.ATR_LENGTH)
    if atr is None or atr.empty or pd.isna(atr.iloc[-1]):
        return None
        
    last_atr = atr.iloc[-1]
    last_close = df['close'].iloc[-1]
    
    # TP/SL کا حساب لگائیں
    tp_buy = last_close + (last_atr * atr_multiplier)
    sl_buy = last_close - last_atr
    
    tp_sell = last_close - (last_atr * atr_multiplier)
    sl_sell = last_close + last_atr
    
    return (tp_buy, sl_buy), (tp_sell, sl_sell)

def generate_core_signal(candles: List[Candle]) -> Dict[str, str]:
    if len(candles) < config.SMA_LONG_PERIOD:
        return {"signal": "wait"}

    df = pd.DataFrame([c.dict() for c in candles])
    close_series = df['close']
    
    # تمام اشاروں کا حساب لگائیں
    sma_short = ta.sma(close_series, length=config.SMA_SHORT_PERIOD)
    sma_long = ta.sma(close_series, length=config.SMA_LONG_PERIOD)
    rsi = ta.rsi(close_series, length=config.RSI_PERIOD)
    macd_data = ta.macd(close_series, fast=config.MACD_FAST, slow=config.MACD_SLOW, signal=config.MACD_SIGNAL)
    
    if any(s is None or s.empty for s in [sma_short, sma_long, rsi, macd_data]):
        return {"signal": "wait"}

    # تازہ ترین اقدار حاصل کریں
    last_sma_short = sma_short.iloc[-1]
    last_sma_long = sma_long.iloc[-1]
    prev_sma_short = sma_short.iloc[-2]
    prev_sma_long = sma_long.iloc[-2]
    last_rsi = rsi.iloc[-1]
    last_macd_line = macd_data.iloc[-1, 0]
    last_macd_signal = macd_data.iloc[-1, 1]
    prev_macd_line = macd_data.iloc[-2, 0]
    prev_macd_signal = macd_data.iloc[-2, 1]

    buy_signals = 0
    sell_signals = 0

    # SMA کراس اوور
    if last_sma_short > last_sma_long and prev_sma_short <= prev_sma_long: buy_signals += 1
    if last_sma_short < last_sma_long and prev_sma_short >= prev_sma_long: sell_signals += 1
    
    # RSI
    if last_rsi < 30: buy_signals += 1
    if last_rsi > 70: sell_signals += 1
    
    # MACD کراس اوور
    if last_macd_line > last_macd_signal and prev_macd_line <= prev_macd_signal: buy_signals += 1
    if last_macd_line < last_macd_signal and prev_macd_line >= prev_macd_signal: sell_signals += 1

    # بنیادی رجحان کا تعین SMA کی بنیاد پر کریں
    trend_signal = "wait"
    if last_sma_short > last_sma_long:
        trend_signal = "buy"
    elif last_sma_short < last_sma_long:
        trend_signal = "sell"

    # حتمی فیصلہ
    if buy_signals > sell_signals:
        return {"signal": "buy"}
    if sell_signals > buy_signals:
        return {"signal": "sell"}
    
    # اگر کوئی واضح کراس اوور نہیں ہے تو رجحان کی پیروی کریں
    return {"signal": trend_signal}
    
