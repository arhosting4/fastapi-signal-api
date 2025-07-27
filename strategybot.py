# filename: strategybot.py

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional, Dict, Any

# ==============================================================================
# حکمت عملی کے پیرامیٹرز اور وزن
# ==============================================================================
EMA_SHORT_PERIOD = 10
EMA_LONG_PERIOD = 30
RSI_PERIOD = 14
STOCH_K = 14
STOCH_D = 3
ATR_LENGTH = 14

# ★★★ اسکورنگ کے لیے وزن ★★★
WEIGHTS = {
    "ema_cross": 0.35,      # 35%
    "rsi_position": 0.25,   # 25%
    "stoch_position": 0.25, # 25%
    "price_action": 0.15    # 15%
}
# ==============================================================================

# (انڈیکیٹر کیلکولیشن فنکشنز ویسے ہی رہیں گے)
def calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, 1e-9) 
    return 100 - (100 / (1 + rs))

def calculate_stoch(high: pd.Series, low: pd.Series, close: pd.Series, k: int, d: int) -> pd.DataFrame:
    low_k = low.rolling(window=k).min()
    high_k = high.rolling(window=k).max()
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
    else: return None
    return tp, sl

# ★★★ نیا فنکشن: بنیادی حکمت عملی کا اسکور پیدا کرنے والا ★★★
def generate_technical_analysis_score(candles: List[Dict]) -> Dict[str, Any]:
    """
    مختلف تکنیکی اشاروں کی بنیاد پر ایک وزنی اسکور (-100 سے +100) پیدا کرتا ہے۔
    +100: انتہائی تیزی (Strongly Bullish)
    -100: انتہائی مندی (Strongly Bearish)
    """
    if len(candles) < max(EMA_LONG_PERIOD, RSI_PERIOD):
        return {"score": 0, "indicators": {}, "reason": "ناکافی ڈیٹا"}

    df = pd.DataFrame(candles)
    close = df['close']
    
    # انڈیکیٹرز کا حساب لگائیں
    ema_fast = close.ewm(span=EMA_SHORT_PERIOD, adjust=False).mean()
    ema_slow = close.ewm(span=EMA_LONG_PERIOD, adjust=False).mean()
    rsi = calculate_rsi(close, RSI_PERIOD)
    stoch = calculate_stoch(df['high'], df['low'], close, STOCH_K, STOCH_D)

    # آخری قدریں حاصل کریں
    last_ema_fast = ema_fast.iloc[-1]
    last_ema_slow = ema_slow.iloc[-1]
    last_rsi = rsi.iloc[-1]
    last_stoch_k = stoch['STOCHk'].iloc[-1]
    last_close = close.iloc[-1]
    prev_close = close.iloc[-2]

    if any(pd.isna(v) for v in [last_ema_fast, last_ema_slow, last_rsi, last_stoch_k]):
        return {"score": 0, "indicators": {}, "reason": "انڈیکیٹر کیلکولیشن میں خرابی"}

    # ہر جزو کے لیے اسکور کا حساب لگائیں (-1 سے +1 تک)
    ema_score = 1 if last_ema_fast > last_ema_slow else -1
    rsi_score = 1 if last_rsi > 52 else (-1 if last_rsi < 48 else 0) # 48-52 نیوٹرل زون
    stoch_score = 1 if last_stoch_k > last_stoch_k.rolling(window=3).mean().iloc[-1] and last_stoch_k < 80 else \
                 (-1 if last_stoch_k < last_stoch_k.rolling(window=3).mean().iloc[-1] and last_stoch_k > 20 else 0)
    price_action_score = 1 if last_close > prev_close else -1

    # وزنی کل اسکور کا حساب لگائیں
    total_score = (
        (ema_score * WEIGHTS["ema_cross"]) +
        (rsi_score * WEIGHTS["rsi_position"]) +
        (stoch_score * WEIGHTS["stoch_position"]) +
        (price_action_score * WEIGHTS["price_action"])
    ) * 100

    indicators_data = {
        "ema_fast": round(last_ema_fast, 5),
        "ema_slow": round(last_ema_slow, 5),
        "rsi": round(last_rsi, 2),
        "stoch_k": round(last_stoch_k, 2),
        "technical_score": round(total_score, 2)
    }

    return {"score": total_score, "indicators": indicators_data, "reason": "تجزیہ مکمل"}
    
