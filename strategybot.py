# filename: strategybot.py

import pandas as pd
import pandas_ta as ta
from typing import List, Dict, Optional, Tuple

def generate_core_signal(candles: List[Dict]) -> Dict[str, str]:
    """
    صرف 15 منٹ کی کینڈلز کی بنیاد پر بنیادی سگنل بناتا ہے۔
    (EMA کراس اوور اور Stochastic کا استعمال)
    """
    if len(candles) < 30:
        return {"signal": "wait"}

    df = pd.DataFrame(candles)
    close = df['close']
    
    ema_fast = ta.ema(close, length=10)
    ema_slow = ta.ema(close, length=30)
    stoch = ta.stoch(df['high'], df['low'], close, k=14, d=3)
    
    if any(s is None or s.empty for s in [ema_fast, ema_slow, stoch]):
        return {"signal": "wait"}

    if ema_fast.iloc[-1] > ema_slow.iloc[-1] and stoch.iloc[-1, 0] < 35:
        return {"signal": "buy"}
    
    if ema_fast.iloc[-1] < ema_slow.iloc[-1] and stoch.iloc[-1, 0] > 65:
        return {"signal": "sell"}
        
    return {"signal": "wait"}

def calculate_tp_sl(candles: List[Dict], signal_type: str) -> Optional[Tuple[float, float]]:
    """
    ATR کی بنیاد پر TP/SL کا حساب لگاتا ہے۔
    """
    if len(candles) < 20: return None
    df = pd.DataFrame(candles)
    atr = ta.atr(df['high'], df['low'], df['close'], length=14)
    if atr is None or atr.empty or pd.isna(atr.iloc[-1]): return None
        
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
    
