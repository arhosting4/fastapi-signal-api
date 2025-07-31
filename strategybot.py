# filename: strategybot.py

import pandas as pd
import numpy as np
import json
import logging
from typing import List, Tuple, Optional, Dict, Any

from level_analyzer import find_optimal_tp_sl
from config import TECHNICAL_ANALYSIS

logger = logging.getLogger(__name__)
WEIGHTS_FILE = "strategy_weights.json"

# --- کنفیگریشن سے پیرامیٹرز ---
EMA_SHORT_PERIOD = TECHNICAL_ANALYSIS["EMA_SHORT_PERIOD"]
EMA_LONG_PERIOD = TECHNICAL_ANALYSIS["EMA_LONG_PERIOD"]
RSI_PERIOD = TECHNICAL_ANALYSIS["RSI_PERIOD"]
STOCH_K = TECHNICAL_ANALYSIS["STOCH_K"]
STOCH_D = TECHNICAL_ANALYSIS["STOCH_D"]
SUPERTREND_ATR = TECHNICAL_ANALYSIS["SUPERTREND_ATR"]
SUPERTREND_FACTOR = TECHNICAL_ANALYSIS["SUPERTREND_FACTOR"]

def _load_weights() -> Dict[str, float]:
    try:
        with open(WEIGHTS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning(f"{WEIGHTS_FILE} نہیں ملی یا خراب ہے۔ ڈیفالٹ وزن استعمال کیا جا رہا ہے۔")
        return {
            "ema_cross": 0.30, "rsi_position": 0.20, "stoch_position": 0.20,
            "price_action": 0.10, "supertrend_confirm": 0.20
        }

def calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    delta = data.diff(1)
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()

    rs = avg_gain / avg_loss.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def calculate_stoch(high: pd.Series, low: pd.Series, close: pd.Series, k: int, d: int) -> pd.DataFrame:
    low_k = low.rolling(window=k, min_periods=1).min()
    high_k = high.rolling(window=k, min_periods=1).max()
    
    stoch_k = 100 * (close - low_k) / (high_k - low_k).replace(0, 1e-9)
    stoch_d = stoch_k.rolling(window=d, min_periods=1).mean()
    
    stoch_df = pd.DataFrame({'STOCHk': stoch_k, 'STOCHd': stoch_d})
    return stoch_df.fillna(50)

def calculate_supertrend(df: pd.DataFrame, atr_period: int, multiplier: float) -> pd.DataFrame:
    high, low, close = df['high'], df['low'], df['close']
    
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)
    atr = tr.ewm(alpha=1/atr_period, adjust=False).mean()
    
    hl2 = (high + low) / 2
    df['upperband'] = hl2 + (multiplier * atr)
    df['lowerband'] = hl2 - (multiplier * atr)
    df['in_uptrend'] = True

    for i in range(1, len(df)):
        if close.iloc[i] > df['upperband'].iloc[i-1]:
            df.loc[df.index[i], 'in_uptrend'] = True
        elif close.iloc[i] < df['lowerband'].iloc[i-1]:
            df.loc[df.index[i], 'in_uptrend'] = False
        else:
            df.loc[df.index[i], 'in_uptrend'] = df['in_uptrend'].iloc[i-1]
    return df

# ★★★ اپ ڈیٹ شدہ فنکشن دستخط ★★★
def generate_technical_analysis_score(df: pd.DataFrame) -> Dict[str, Any]:
    if len(df) < max(EMA_LONG_PERIOD, RSI_PERIOD, 34):
        return {"score": 0, "indicators": {}, "reason": "ناکافی ڈیٹا"}

    # اب ڈیٹا فریم بنانے کی ضرورت نہیں
    close = df['close']
    
    WEIGHTS = _load_weights()
    
    ema_fast = close.ewm(span=EMA_SHORT_PERIOD, adjust=False).mean()
    ema_slow = close.ewm(span=EMA_LONG_PERIOD, adjust=False).mean()
    rsi = calculate_rsi(close, RSI_PERIOD)
    stoch = calculate_stoch(df['high'], df['low'], close, STOCH_K, STOCH_D)
    df_supertrend = calculate_supertrend(df.copy(), SUPERTREND_ATR, SUPERTREND_FACTOR) # کاپی پر کام کریں
    
    last_ema_fast, last_ema_slow = ema_fast.iloc[-1], ema_slow.iloc[-1]
    last_rsi, last_stoch_k = rsi.iloc[-1], stoch['STOCHk'].iloc[-1]
    last_close, prev_close = close.iloc[-1], close.iloc[-2]
    in_uptrend = df_supertrend['in_uptrend'].iloc[-1]

    if any(pd.isna(v) for v in [last_ema_fast, last_ema_slow, last_rsi, last_stoch_k]):
        return {"score": 0, "indicators": {}, "reason": "انڈیکیٹر کیلکولیشن میں خرابی"}

    ema_score = 1 if last_ema_fast > last_ema_slow else -1
    rsi_score = 1 if last_rsi > 52 else (-1 if last_rsi < 48 else 0)
    stoch_score = 1 if last_stoch_k > 52 else (-1 if last_stoch_k < 48 else 0)
    price_action_score = 1 if last_close > prev_close else -1
    supertrend_score = 1 if in_uptrend else -1

    total_score = (
        (ema_score * WEIGHTS["ema_cross"]) +
        (rsi_score * WEIGHTS["rsi_position"]) +
        (stoch_score * WEIGHTS["stoch_position"]) +
        (price_action_score * WEIGHTS["price_action"]) +
        (supertrend_score * WEIGHTS["supertrend_confirm"])
    ) * 100

    indicators_data = {
        "ema_fast": round(last_ema_fast, 5), "ema_slow": round(last_ema_slow, 5),
        "rsi": round(last_rsi, 2), "stoch_k": round(last_stoch_k, 2),
        "supertrend_direction": "Up" if in_uptrend else "Down",
        "technical_score": round(total_score, 2),
        "component_scores": {
            "ema_cross": ema_score, "rsi_position": rsi_score,
            "stoch_position": stoch_score, "price_action": price_action_score,
            "supertrend_confirm": supertrend_score
        }
    }

    return {"score": total_score, "indicators": indicators_data, "reason": "تجزیہ مکمل"}

# ★★★ اپ ڈیٹ شدہ فنکشن دستخط ★★★
def calculate_tp_sl(df: pd.DataFrame, signal_type: str) -> Optional[Tuple[float, float]]:
    if df.empty or len(df) < 34:
        return None
    try:
        # find_optimal_tp_sl کو اب ڈکشنری کی فہرست کے بجائے ڈیٹا فریم کی ضرورت ہوگی
        optimal_levels = find_optimal_tp_sl(df, signal_type)
        if optimal_levels:
            return optimal_levels
        
        return None
    except Exception as e:
        logging.error(f"TP/SL کیلکولیشن میں خرابی: {e}", exc_info=True)
        return None
    
