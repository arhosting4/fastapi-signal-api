# filename: strategybot.py

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional, Dict, Any

# --- حکمت عملی کے پیرامیٹرز اور وزن ---
# ★★★ نئے انڈیکیٹرز کے لیے پیرامیٹرز شامل کیے گئے ★★★
EMA_SHORT_PERIOD = 10
EMA_LONG_PERIOD = 30
RSI_PERIOD = 14
STOCH_K = 14
STOCH_D = 3
ATR_LENGTH = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 3.0

# ★★★ وزن کو نئے انڈیکیٹرز کو شامل کرنے کے لیے ایڈجسٹ کیا گیا ★★★
WEIGHTS = {
    "ema_cross": 0.25,
    "rsi_position": 0.15,
    "stoch_position": 0.15,
    "price_action": 0.10,
    "macd_signal": 0.20,      # نیا وزن
    "supertrend_signal": 0.15 # نیا وزن
}

# --- انڈیکیٹر کیلکولیشن فنکشنز ---

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

# ★★★ نیا فنکشن: MACD کا حساب لگانے کے لیے ★★★
def calculate_macd(close: pd.Series, fast: int, slow: int, signal: int) -> pd.DataFrame:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame({'MACD_line': macd_line, 'Signal_line': signal_line, 'Histogram': histogram})

# ★★★ نیا فنکشن: Supertrend کا حساب لگانے کے لیے ★★★
def calculate_supertrend(high: pd.Series, low: pd.Series, close: pd.Series, period: int, multiplier: float) -> pd.DataFrame:
    hl2 = (high + low) / 2
    df = pd.DataFrame(index=high.index)
    df['h-l'] = high - low
    df['h-pc'] = np.abs(high - close.shift())
    df['l-pc'] = np.abs(low - close.shift())
    tr = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    supertrend = pd.Series(np.nan, index=high.index)
    trend = pd.Series(1, index=high.index)

    for i in range(1, len(close)):
        if close.iloc[i] > upper_band.iloc[i-1]:
            trend.iloc[i] = 1
        elif close.iloc[i] < lower_band.iloc[i-1]:
            trend.iloc[i] = -1
        else:
            trend.iloc[i] = trend.iloc[i-1]

        if trend.iloc[i] == 1:
            lower_band.iloc[i] = max(lower_band.iloc[i], lower_band.iloc[i-1])
            supertrend.iloc[i] = lower_band.iloc[i]
        else:
            upper_band.iloc[i] = min(upper_band.iloc[i], upper_band.iloc[i-1])
            supertrend.iloc[i] = upper_band.iloc[i]
            
    return pd.DataFrame({'Supertrend': supertrend, 'Trend': trend})


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

# --- بنیادی حکمت عملی کا اسکور پیدا کرنے والا فنکشن ---

def generate_technical_analysis_score(candles: List[Dict]) -> Dict[str, Any]:
    """مختلف تکنیکی اشاروں کی بنیاد پر ایک وزنی اسکور (-100 سے +100) پیدا کرتا ہے۔"""
    required_length = max(EMA_LONG_PERIOD, RSI_PERIOD, MACD_SLOW)
    if len(candles) < required_length:
        return {"score": 0, "indicators": {}, "reason": "ناکافی ڈیٹا"}

    df = pd.DataFrame(candles)
    close = df['close']
    
    # ★★★ تمام انڈیکیٹرز کا حساب لگانا ★★★
    ema_fast = close.ewm(span=EMA_SHORT_PERIOD, adjust=False).mean()
    ema_slow = close.ewm(span=EMA_LONG_PERIOD, adjust=False).mean()
    rsi = calculate_rsi(close, RSI_PERIOD)
    stoch = calculate_stoch(df['high'], df['low'], close, STOCH_K, STOCH_D)
    macd = calculate_macd(close, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    supertrend = calculate_supertrend(df['high'], df['low'], close, SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER)

    # آخری قدریں حاصل کرنا
    last_ema_fast = ema_fast.iloc[-1]
    last_ema_slow = ema_slow.iloc[-1]
    last_rsi = rsi.iloc[-1]
    last_stoch_k = stoch['STOCHk'].iloc[-1]
    last_stoch_d = stoch['STOCHd'].iloc[-1]
    last_macd_line = macd['MACD_line'].iloc[-1]
    last_macd_signal = macd['Signal_line'].iloc[-1]
    last_supertrend_trend = supertrend['Trend'].iloc[-1]
    last_close = close.iloc[-1]
    prev_close = close.iloc[-2]

    if any(pd.isna(v) for v in [last_ema_fast, last_ema_slow, last_rsi, last_stoch_k, last_stoch_d, last_macd_line, last_macd_signal, last_supertrend_trend]):
        return {"score": 0, "indicators": {}, "reason": "انڈیکیٹر کیلکولیشن میں خرابی"}

    # ★★★ ہر انڈیکیٹر کے لیے اسکور کا حساب لگانا ★★★
    ema_score = 1 if last_ema_fast > last_ema_slow else -1
    rsi_score = 1 if last_rsi > 52 else (-1 if last_rsi < 48 else 0)
    stoch_score = 1 if last_stoch_k > last_stoch_d and last_stoch_k < 80 else \
                 (-1 if last_stoch_k < last_stoch_d and last_stoch_k > 20 else 0)
    price_action_score = 1 if last_close > prev_close else -1
    macd_score = 1 if last_macd_line > last_macd_signal else -1
    supertrend_score = 1 if last_supertrend_trend == 1 else -1

    # ★★★ تمام اسکورز کو وزن کے ساتھ جمع کرنا ★★★
    total_score = (
        (ema_score * WEIGHTS["ema_cross"]) +
        (rsi_score * WEIGHTS["rsi_position"]) +
        (stoch_score * WEIGHTS["stoch_position"]) +
        (price_action_score * WEIGHTS["price_action"]) +
        (macd_score * WEIGHTS["macd_signal"]) +
        (supertrend_score * WEIGHTS["supertrend_signal"])
    ) * 100

    # فرنٹ اینڈ اور reasonbot کے لیے ڈیٹا تیار کرنا
    indicators_data = {
        "ema_fast": round(last_ema_fast, 5),
        "ema_slow": round(last_ema_slow, 5),
        "rsi": round(last_rsi, 2),
        "stoch_k": round(last_stoch_k, 2),
        "macd_line": round(last_macd_line, 5),
        "macd_signal_line": round(last_macd_signal, 5),
        "supertrend_direction": "Up" if last_supertrend_trend == 1 else "Down",
        "technical_score": round(total_score, 2)
    }

    return {"score": total_score, "indicators": indicators_data, "reason": "تجزیہ مکمل"}
    
