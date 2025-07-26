# filename: strategybot.py

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional, Dict

# ==============================================================================
# حکمت عملی کے پیرامیٹرز (RSI کے بغیر)
# ==============================================================================
EMA_SHORT_PERIOD = 10
EMA_LONG_PERIOD = 30
STOCH_K = 14
STOCH_D = 3
ATR_LENGTH = 14
# ==============================================================================

# ★★★ صرف بنیادی اور قابل اعتماد انڈیکیٹرز ★★★
def calculate_stoch(high: pd.Series, low: pd.Series, close: pd.Series, k: int, d: int) -> pd.DataFrame:
    low_k = low.rolling(window=k).min()
    high_k = high.rolling(window=k).max()
    # صفر سے تقسیم کے مسئلے کو حل کرنا
    stoch_k = 100 * (close - low_k) / (high_k - low_k).replace(0, 1e-9)
    stoch_d = stoch_k.rolling(window=d).mean()
    return pd.DataFrame({'STOCHk': stoch_k, 'STOCHd': stoch_d})

def calculate_tp_sl(candles: List[Dict], signal_type: str) -> Optional[Tuple[float, float]]:
    if len(candles) < 20: return None
    df = pd.DataFrame(candles)
    df['h-l'] = df['high'] - df['low']
    df['h-pc'] = np.abs(df['high'] - df['close'].shift())
    df['l-pc'] = np.abs(df['low'] - df['close'].shift())
    tr = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    atr = tr.rolling(window=ATR_LENGTH).mean()
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
    RSI کے بغیر، صرف EMA اور Stochastic پر مبنی سگنل کی منطق۔
    """
    if len(candles) < EMA_LONG_PERIOD:
        return {"signal": "wait", "indicators": {}}
    
    df = pd.DataFrame(candles)
    close = df['close']
    
    ema_fast = close.ewm(span=EMA_SHORT_PERIOD, adjust=False).mean()
    ema_slow = close.ewm(span=EMA_LONG_PERIOD, adjust=False).mean()
    stoch = calculate_stoch(df['high'], df['low'], close, STOCH_K, STOCH_D)
    
    if any(s.empty for s in [ema_fast, ema_slow, stoch]):
        return {"signal": "wait", "indicators": {}}

    # آخری قدریں حاصل کریں
    last_ema_fast = ema_fast.iloc[-1]
    last_ema_slow = ema_slow.iloc[-1]
    last_stoch_k = stoch['STOCHk'].iloc[-1]

    if any(pd.isna(v) for v in [last_ema_fast, last_ema_slow, last_stoch_k]):
        return {"signal": "wait", "indicators": {}}

    indicators_data = {
        "ema_cross": "bullish" if last_ema_fast > last_ema_slow else "bearish",
        "stoch_k": round(last_stoch_k, 2)
    }

    # سگنل کی شرائط کو سادہ کر دیا گیا ہے
    buy_conditions = [
        last_ema_fast > last_ema_slow,
        last_stoch_k < 35  # Stochastic کی شرط
    ]

    sell_conditions = [
        last_ema_fast < last_ema_slow,
        last_stoch_k > 65  # Stochastic کی شرط
    ]

    if all(buy_conditions):
        return {"signal": "buy", "indicators": indicators_data}
    
    if all(sell_conditions):
        return {"signal": "sell", "indicators": indicators_data}
        
    return {"signal": "wait", "indicators": {}}
    
