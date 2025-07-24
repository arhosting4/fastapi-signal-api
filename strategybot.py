# filename: strategybot.py
import pandas as pd
import pandas_ta as ta
from typing import List, Tuple, Optional, Dict

import config
from schemas import Candle

def calculate_tp_sl(candles: List[Candle], signal_type: str) -> Optional[Tuple[float, float]]:
    if len(candles) < 20:
        return None
    
    df = pd.DataFrame([c.dict() for c in candles])
    
    atr = ta.atr(df['high'], df['low'], df['close'], length=config.ATR_LENGTH)
    if atr is None or atr.empty or pd.isna(atr.iloc[-1]):
        return None
        
    last_atr = atr.iloc[-1]
    last_close = df['close'].iloc[-1]
    
    recent_high = df['high'].tail(10).max()
    recent_low = df['low'].tail(10).min()
    
    if signal_type == "buy":
        sl = recent_low - (last_atr * 0.5)
        tp = last_close + (last_close - sl) * 1.5
    elif signal_type == "sell":
        sl = recent_high + (last_atr * 0.5)
        tp = last_close - (sl - last_close) * 1.5
    else:
        return None

    return tp, sl

def generate_core_signal(candles: List[Candle]) -> Dict[str, str]:
    if len(candles) < config.BBANDS_PERIOD:
        return {"signal": "wait"}

    df = pd.DataFrame([c.dict() for c in candles])
    close = df['close']
    
    ema_fast = ta.ema(close, length=config.EMA_SHORT_PERIOD)
    ema_slow = ta.ema(close, length=config.EMA_LONG_PERIOD)
    stoch = ta.stoch(df['high'], df['low'], close, k=config.STOCH_K, d=config.STOCH_D)
    bbands = ta.bbands(close, length=config.BBANDS_PERIOD)

    if any(s is None or s.empty for s in [ema_fast, ema_slow, stoch, bbands]):
        return {"signal": "wait"}

    last_close = close.iloc[-1]
    last_ema_fast = ema_fast.iloc[-1]
    last_ema_slow = ema_slow.iloc[-1]
    last_stoch_k = stoch.iloc[-1, 0]
    last_bb_lower = bbands.iloc[-1, 0]
    last_bb_upper = bbands.iloc[-1, 2]

    buy_conditions = [
        last_ema_fast > last_ema_slow,
        last_stoch_k < 30,
        last_close < last_bb_lower
    ]
    sell_conditions = [
        last_ema_fast < last_ema_slow,
        last_stoch_k > 70,
        last_close > last_bb_upper
    ]

    if sum(buy_conditions) >= 2:
        return {"signal": "buy"}
    if sum(sell_conditions) >= 2:
        return {"signal": "sell"}
        
    return {"signal": "wait"}
    
