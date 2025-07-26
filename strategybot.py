# filename: strategybot.py

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional, Dict

# ==============================================================================
# حکمت عملی کے پیرامیٹرز (صرف EMA اور ATR)
# ==============================================================================
EMA_SHORT_PERIOD = 10
EMA_LONG_PERIOD = 30
ATR_LENGTH = 14
# ==============================================================================

def calculate_tp_sl(candles: List[Dict], signal_type: str) -> Optional[Tuple[float, float]]:
    """
    TP/SL کا حساب لگانے کے لیے سادہ اور محفوظ منطق۔
    """
    if len(candles) < 20: return None
    df = pd.DataFrame(candles)
    
    # ATR کی سادہ کیلکولیشن
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(window=ATR_LENGTH).mean()
    
    if atr.empty or pd.isna(atr.iloc[-1]): return None
    
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

def generate_core_signal(candles: List[Dict]) -> Dict[str, Any]:
    """
    انتہائی سادہ منطق: صرف EMA کراس اوور پر مبنی سگنل۔
    """
    if len(candles) < EMA_LONG_PERIOD:
        return {"signal": "wait", "indicators": {}}
    
    df = pd.DataFrame(candles)
    close = df['close']
    
    # صرف EMA کا حساب لگائیں
    ema_fast = close.ewm(span=EMA_SHORT_PERIOD, adjust=False).mean()
    ema_slow = close.ewm(span=EMA_LONG_PERIOD, adjust=False).mean()
    
    if ema_fast.empty or ema_slow.empty or pd.isna(ema_fast.iloc[-1]) or pd.isna(ema_slow.iloc[-1]):
        return {"signal": "wait", "indicators": {}}

    # آخری قدریں حاصل کریں
    last_ema_fast = ema_fast.iloc[-1]
    last_ema_slow = ema_slow.iloc[-1]
    prev_ema_fast = ema_fast.iloc[-2]
    prev_ema_slow = ema_slow.iloc[-2]

    indicators_data = {
        "ema_cross": "bullish" if last_ema_fast > last_ema_slow else "bearish"
    }

    # خریدنے کی شرط: جب تیز EMA سست EMA کو نیچے سے اوپر کی طرف کراس کرے
    if last_ema_fast > last_ema_slow and prev_ema_fast <= prev_ema_slow:
        return {"signal": "buy", "indicators": indicators_data}
    
    # بیچنے کی شرط: جب تیز EMA سست EMA کو اوپر سے نیچے کی طرف کراس کرے
    if last_ema_fast < last_ema_slow and prev_ema_fast >= prev_ema_slow:
        return {"signal": "sell", "indicators": indicators_data}
        
    return {"signal": "wait", "indicators": {}}
    
