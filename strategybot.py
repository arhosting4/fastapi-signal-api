# filename: strategybot.py

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional, Dict, Any

# --- حکمت عملی کے پیرامیٹرز اور وزن ---
EMA_SHORT_PERIOD = 10
EMA_LONG_PERIOD = 30
RSI_PERIOD = 14
STOCH_K = 14
STOCH_D = 3
ATR_LENGTH = 14
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 3
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# ★★★ نئے، زیادہ متوازن وزن ★★★
WEIGHTS = {
    "ema_cross": 0.30,
    "rsi_position": 0.15,
    "stoch_position": 0.15,
    "supertrend_confirm": 0.20,
    "macd_confirm": 0.10,
    "price_action": 0.10
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

def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    df = pd.DataFrame({'high': high, 'low': low, 'close': close})
    df['h-l'] = df['high'] - df['low']
    df['h-pc'] = np.abs(df['high'] - df['close'].shift())
    df['l-pc'] = np.abs(df['low'] - df['close'].shift())
    tr = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    return tr.rolling(window=period).mean()

def calculate_supertrend(high: pd.Series, low: pd.Series, close: pd.Series, period: int, multiplier: float) -> pd.DataFrame:
    atr = calculate_atr(high, low, close, period)
    hl2 = (high + low) / 2
    final_upper_band = upper_band = hl2 + (multiplier * atr)
    final_lower_band = lower_band = hl2 - (multiplier * atr)
    supertrend = pd.Series(np.nan, index=close.index)

    for i in range(1, len(close)):
        if close.iloc[i] > final_upper_band.iloc[i-1]:
            supertrend.iloc[i] = 1
        elif close.iloc[i] < final_lower_band.iloc[i-1]:
            supertrend.iloc[i] = -1
        else:
            supertrend.iloc[i] = supertrend.iloc[i-1]
            if supertrend.iloc[i] == -1 and lower_band.iloc[i] < final_lower_band.iloc[i-1]:
                final_lower_band.iloc[i] = lower_band.iloc[i]
            if supertrend.iloc[i] == 1 and upper_band.iloc[i] > final_upper_band.iloc[i-1]:
                final_upper_band.iloc[i] = upper_band.iloc[i]

    return pd.DataFrame({'supertrend': supertrend, 'final_upper': final_upper_band, 'final_lower': final_lower_band})

def calculate_macd(close: pd.Series, fast: int, slow: int, signal: int) -> pd.DataFrame:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({'MACD': macd, 'Signal': signal_line})

# ==============================================================================
# ★★★ نیا، ذہین، اور متحرک TP/SL کیلکولیشن فنکشن ★★★
# ==============================================================================
def calculate_tp_sl(candles: List[Dict], signal_type: str) -> Optional[Tuple[float, float]]:
    """
    ATR اور اہم سوئنگ پوائنٹس کی بنیاد پر ایک ذہین TP/SL کا حساب لگاتا ہے۔
    """
    if len(candles) < 50: return None
    df = pd.DataFrame(candles)
    
    # ڈیٹا کی قسموں کو یقینی بنائیں
    for col in ['high', 'low', 'close', 'open']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.dropna(inplace=True)
    if len(df) < 50: return None

    last_candle = df.iloc[-1]
    last_close = last_candle['close']
    
    # 1. ATR کی بنیاد پر اسٹاپ لاس (SL)
    atr = calculate_atr(df['high'], df['low'], df['close'], ATR_LENGTH)
    if atr.empty or pd.isna(atr.iloc[-1]): return None
    last_atr = atr.iloc[-1]
    
    sl_multiplier = 2.0  # ATR کا ضرب، اسے ایڈجسٹ کیا جا سکتا ہے
    sl = 0.0
    if signal_type == "buy":
        sl = last_close - (last_atr * sl_multiplier)
    elif signal_type == "sell":
        sl = last_close + (last_atr * sl_multiplier)
    else:
        return None

    # 2. اہم سوئنگ پوائنٹس کی بنیاد پر ٹیک پرافٹ (TP)
    # پچھلی 50 کینڈلز میں اہم اونچائی اور کمی کو تلاش کریں
    recent_highs = df['high'].tail(50).sort_values(ascending=False)
    recent_lows = df['low'].tail(50).sort_values(ascending=True)

    tp = 0.0
    if signal_type == "buy":
        # اگلی ممکنہ مزاحمت (resistance) تلاش کریں
        next_resistance = recent_highs[recent_highs > last_close].iloc[0] if not recent_highs[recent_highs > last_close].empty else None
        # اگر مزاحمت ملتی ہے، تو TP کو اس سے تھوڑا پہلے رکھیں
        if next_resistance:
            tp = next_resistance - (last_atr * 0.25) # مزاحمت سے تھوڑا پہلے
        else:
            # اگر کوئی واضح مزاحمت نہیں، تو 1:1.5 رسک/ریوارڈ استعمال کریں
            tp = last_close + (last_close - sl) * 1.5
    
    elif signal_type == "sell":
        # اگلی ممکنہ سپورٹ تلاش کریں
        next_support = recent_lows[recent_lows < last_close].iloc[0] if not recent_lows[recent_lows < last_close].empty else None
        # اگر سپورٹ ملتی ہے، تو TP کو اس سے تھوڑا پہلے رکھیں
        if next_support:
            tp = next_support + (last_atr * 0.25) # سپورٹ سے تھوڑا پہلے
        else:
            # اگر کوئی واضح سپورٹ نہیں، تو 1:1.5 رسک/ریوارڈ استعمال کریں
            tp = last_close - (sl - last_close) * 1.5

    # 3. یقینی بنائیں کہ TP/SL منطقی ہیں
    # کم از کم رسک/ریوارڈ 1:1 ہونا چاہیے
    if signal_type == "buy" and (tp - last_close) < (last_close - sl):
        tp = last_close + (last_close - sl) # کم از کم 1:1
    elif signal_type == "sell" and (last_close - tp) < (sl - last_close):
        tp = last_close - (sl - last_close) # کم از کم 1:1

    return tp, sl

# --- بنیادی حکمت عملی کا اسکور پیدا کرنے والا فنکشن ---
def generate_technical_analysis_score(candles: List[Dict]) -> Dict[str, Any]:
    if len(candles) < max(EMA_LONG_PERIOD, RSI_PERIOD, MACD_SLOW):
        return {"score": 0, "indicators": {}, "reason": "ناکافی ڈیٹا"}

    df = pd.DataFrame(candles)
    close = df['close']
    
    # تمام انڈیکیٹرز کا حساب لگائیں
    ema_fast = close.ewm(span=EMA_SHORT_PERIOD, adjust=False).mean()
    ema_slow = close.ewm(span=EMA_LONG_PERIOD, adjust=False).mean()
    rsi = calculate_rsi(close, RSI_PERIOD)
    stoch = calculate_stoch(df['high'], df['low'], close, STOCH_K, STOCH_D)
    supertrend = calculate_supertrend(df['high'], df['low'], close, SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER)
    macd = calculate_macd(close, MACD_FAST, MACD_SLOW, MACD_SIGNAL)

    # آخری ویلیوز حاصل کریں
    last_ema_fast, last_ema_slow = ema_fast.iloc[-1], ema_slow.iloc[-1]
    last_rsi = rsi.iloc[-1]
    last_stoch_k, last_stoch_d = stoch['STOCHk'].iloc[-1], stoch['STOCHd'].iloc[-1]
    last_supertrend = supertrend['supertrend'].iloc[-1]
    last_macd, last_signal = macd['MACD'].iloc[-1], macd['Signal'].iloc[-1]
    last_close, prev_close = close.iloc[-1], close.iloc[-2]

    if any(pd.isna(v) for v in [last_ema_fast, last_ema_slow, last_rsi, last_stoch_k, last_stoch_d, last_supertrend, last_macd, last_signal]):
        return {"score": 0, "indicators": {}, "reason": "انڈیکیٹر کیلکولیشن میں خرابی"}

    # اسکورنگ کی منطق
    ema_score = 1 if last_ema_fast > last_ema_slow else -1
    rsi_score = 1 if last_rsi > 55 else (-1 if last_rsi < 45 else 0)
    stoch_score = 1 if last_stoch_k > last_stoch_d and last_stoch_k < 80 else (-1 if last_stoch_k < last_stoch_d and last_stoch_k > 20 else 0)
    supertrend_score = 1 if last_supertrend == 1 else (-1 if last_supertrend == -1 else 0)
    macd_score = 1 if last_macd > last_signal else -1
    price_action_score = 1 if last_close > prev_close else -1

    # وزنی اسکور کا حساب لگائیں
    total_score = (
        (ema_score * WEIGHTS["ema_cross"]) +
        (rsi_score * WEIGHTS["rsi_position"]) +
        (stoch_score * WEIGHTS["stoch_position"]) +
        (supertrend_score * WEIGHTS["supertrend_confirm"]) +
        (macd_score * WEIGHTS["macd_confirm"]) +
        (price_action_score * WEIGHTS["price_action"])
    ) * 100

    indicators_data = {
        "ema_fast": round(last_ema_fast, 5), "ema_slow": round(last_ema_slow, 5),
        "rsi": round(last_rsi, 2), "stoch_k": round(last_stoch_k, 2),
        "supertrend": "Up" if last_supertrend == 1 else "Down",
        "macd": round(last_macd, 5), "macd_signal": round(last_signal, 5),
        "technical_score": round(total_score, 2)
    }

    return {"score": total_score, "indicators": indicators_data, "reason": "تجزیہ مکمل"}
    
