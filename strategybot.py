# filename: strategybot.py

import json
import logging
from typing import Tuple, Optional, Dict, Any

import numpy as np
import pandas as pd

# مقامی امپورٹس
from level_analyzer import find_optimal_tp_sl
# مرکزی کنفیگریشن ماڈیول سے سیٹنگز درآمد کریں
from config import tech_settings

logger = logging.getLogger(__name__)

# --- حکمت عملی کے وزن کی فائل ---
WEIGHTS_FILE = "strategy_weights.json"

# --- کنفیگریشن سے پیرامیٹرز ---
EMA_SHORT_PERIOD = tech_settings.EMA_SHORT_PERIOD
EMA_LONG_PERIOD = tech_settings.EMA_LONG_PERIOD
RSI_PERIOD = tech_settings.RSI_PERIOD
STOCH_K = tech_settings.STOCH_K
STOCH_D = tech_settings.STOCH_D
SUPERTREND_ATR = tech_settings.SUPERTREND_ATR
SUPERTREND_FACTOR = tech_settings.SUPERTREND_FACTOR

def _load_weights() -> Dict[str, float]:
    """
    حکمت عملی کے وزن کو JSON فائل سے محفوظ طریقے سے لوڈ کرتا ہے۔
    اگر فائل نہیں ملتی یا خراب ہے تو ڈیفالٹ وزن واپس کرتا ہے۔
    """
    try:
        with open(WEIGHTS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning(f"'{WEIGHTS_FILE}' نہیں ملی یا خراب ہے۔ ڈیفالٹ وزن استعمال کیا جا رہا ہے۔")
        return {
            "ema_cross": 0.30,
            "rsi_position": 0.20,
            "stoch_position": 0.20,
            "price_action": 0.10,
            "supertrend_confirm": 0.20
        }

# --- کسٹم انڈیکیٹر فنکشنز ---

def _calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    """RSI کا حساب لگاتا ہے۔"""
    delta = data.diff(1)
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, 1e-9) # صفر سے تقسیم سے بچیں
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50) # NaN اقدار کو 50 سے بھریں

def _calculate_stoch(high: pd.Series, low: pd.Series, close: pd.Series, k: int, d: int) -> pd.DataFrame:
    """Stochastic Oscillator (%K اور %D) کا حساب لگاتا ہے۔"""
    low_k = low.rolling(window=k).min()
    high_k = high.rolling(window=k).max()
    
    stoch_k = 100 * (close - low_k) / (high_k - low_k).replace(0, 1e-9)
    stoch_d = stoch_k.rolling(window=d).mean()
    
    return pd.DataFrame({'STOCHk': stoch_k, 'STOCHd': stoch_d}).fillna(50)

def _calculate_supertrend(df: pd.DataFrame, atr_period: int, multiplier: float) -> pd.DataFrame:
    """
    Supertrend انڈیکیٹر کا حساب لگاتا ہے۔
    یہ فنکشن ان پٹ ڈیٹا فریم کی ایک کاپی پر کام کرتا ہے تاکہ سائیڈ ایفیکٹس سے بچا جا سکے۔
    """
    df_copy = df.copy()
    high, low, close = df_copy['high'], df_copy['low'], df_copy['close']
    
    # ATR کا حساب
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)
    atr = tr.ewm(alpha=1/atr_period, adjust=False).mean()
    
    # بالائی اور زیریں بینڈز کا حساب
    df_copy['upperband'] = (high + low) / 2 + (multiplier * atr)
    df_copy['lowerband'] = (high + low) / 2 - (multiplier * atr)
    df_copy['in_uptrend'] = True

    for i in range(1, len(df_copy)):
        if close.iloc[i] > df_copy['upperband'].iloc[i-1]:
            df_copy.loc[df_copy.index[i], 'in_uptrend'] = True
        elif close.iloc[i] < df_copy['lowerband'].iloc[i-1]:
            df_copy.loc[df_copy.index[i], 'in_uptrend'] = False
        else:
            df_copy.loc[df_copy.index[i], 'in_uptrend'] = df_copy['in_uptrend'].iloc[i-1]
            
        # بینڈز کو ایڈجسٹ کریں
        if df_copy['in_uptrend'].iloc[i] and df_copy['lowerband'].iloc[i] < df_copy['lowerband'].iloc[i-1]:
            df_copy.loc[df_copy.index[i], 'lowerband'] = df_copy['lowerband'].iloc[i-1]
        if not df_copy['in_uptrend'].iloc[i] and df_copy['upperband'].iloc[i] > df_copy['upperband'].iloc[i-1]:
            df_copy.loc[df_copy.index[i], 'upperband'] = df_copy['upperband'].iloc[i-1]
            
    return df_copy

# --- مرکزی تجزیاتی فنکشنز ---

def generate_technical_analysis_score(df: pd.DataFrame) -> Dict[str, Any]:
    """
    فراہم کردہ ڈیٹا فریم کی بنیاد پر ایک جامع تکنیکی اسکور اور انڈیکیٹر ڈیٹا تیار کرتا ہے۔
    """
    required_length = max(EMA_LONG_PERIOD, RSI_PERIOD, 34)
    if len(df) < required_length:
        return {"score": 0, "indicators": {}, "reason": f"ناکافی ڈیٹا ({len(df)}/{required_length})"}

    close = df['close']
    WEIGHTS = _load_weights()
    
    # تمام انڈیکیٹرز کا حساب لگائیں
    ema_fast = close.ewm(span=EMA_SHORT_PERIOD, adjust=False).mean()
    ema_slow = close.ewm(span=EMA_LONG_PERIOD, adjust=False).mean()
    rsi = _calculate_rsi(close, RSI_PERIOD)
    stoch = _calculate_stoch(df['high'], df['low'], close, STOCH_K, STOCH_D)
    df_supertrend = _calculate_supertrend(df, SUPERTREND_ATR, SUPERTREND_FACTOR)
    
    # تازہ ترین اقدار حاصل کریں
    last_ema_fast, last_ema_slow = ema_fast.iloc[-1], ema_slow.iloc[-1]
    last_rsi, last_stoch_k = rsi.iloc[-1], stoch['STOCHk'].iloc[-1]
    last_close, prev_close = close.iloc[-1], close.iloc[-2]
    in_uptrend = df_supertrend['in_uptrend'].iloc[-1]

    if any(pd.isna(v) for v in [last_ema_fast, last_ema_slow, last_rsi, last_stoch_k]):
        return {"score": 0, "indicators": {}, "reason": "انڈیکیٹر کیلکولیشن میں خرابی (NaN ویلیو)"}

    # ہر جزو کے لیے اسکور کا حساب لگائیں (-1, 0, 1)
    ema_score = 1 if last_ema_fast > last_ema_slow else -1
    rsi_score = 1 if last_rsi > 52 else (-1 if last_rsi < 48 else 0)
    stoch_score = 1 if last_stoch_k > 52 else (-1 if last_stoch_k < 48 else 0)
    price_action_score = 1 if last_close > prev_close else -1
    supertrend_score = 1 if in_uptrend else -1

    # وزن کی بنیاد پر کل اسکور کا حساب لگائیں
    total_score = (
        (ema_score * WEIGHTS.get("ema_cross", 0.30)) +
        (rsi_score * WEIGHTS.get("rsi_position", 0.20)) +
        (stoch_score * WEIGHTS.get("stoch_position", 0.20)) +
        (price_action_score * WEIGHTS.get("price_action", 0.10)) +
        (supertrend_score * WEIGHTS.get("supertrend_confirm", 0.20))
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

def calculate_tp_sl(df: pd.DataFrame, signal_type: str) -> Optional[Tuple[float, float]]:
    """
    مارکیٹ کی ساخت کی بنیاد پر بہترین TP/SL سطحوں کا حساب لگاتا ہے۔
    """
    if len(df) < 34:
        logger.warning("TP/SL کے حساب کے لیے ناکافی ڈیٹا۔")
        return None
    try:
        return find_optimal_tp_sl(df, signal_type)
    except Exception as e:
        logging.error(f"TP/SL کیلکولیشن میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        return None
    
