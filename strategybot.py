# filename: strategybot.py

import json
import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

# مقامی امپورٹس
from level_analyzer import find_optimal_tp_sl
from config import tech_settings

logger = logging.getLogger(__name__)
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
    """حکمت عملی کے وزن کو JSON فائل سے لوڈ کرتا ہے۔"""
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
    """RSI انڈیکیٹر کا حساب لگاتا ہے۔"""
    delta = data.diff(1)
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def calculate_stoch(high: pd.Series, low: pd.Series, close: pd.Series, k: int, d: int) -> pd.DataFrame:
    """Stochastic Oscillator کا حساب لگاتا ہے۔"""
    low_k = low.rolling(window=k).min()
    high_k = high.rolling(window=k).max()
    stoch_k = 100 * (close - low_k) / (high_k - low_k).replace(0, 1e-9)
    stoch_d = stoch_k.rolling(window=d).mean()
    stoch_df = pd.DataFrame({'STOCHk': stoch_k, 'STOCHd': stoch_d})
    return stoch_df.fillna(50)

def calculate_supertrend(df: pd.DataFrame, atr_period: int, multiplier: float) -> pd.DataFrame:
    """Supertrend انڈیکیٹر کا حساب لگاتا ہے۔"""
    df_copy = df.copy()
    high, low, close = df_copy['high'], df_copy['low'], df_copy['close']
    
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)
    atr = tr.ewm(alpha=1/atr_period, adjust=False).mean()
    
    df_copy['upperband'] = (high + low) / 2 + (multiplier * atr)
    df_copy['lowerband'] = (high + low) / 2 - (multiplier * atr)
    df_copy['in_uptrend'] = True
    
    for i in range(1, len(df_copy)):
        curr = df_copy.index[i]
        prev = df_copy.index[i-1]
        if close[curr] > df_copy.loc[prev, 'upperband']:
            df_copy.loc[curr, 'in_uptrend'] = True
        elif close[curr] < df_copy.loc[prev, 'lowerband']:
            df_copy.loc[curr, 'in_uptrend'] = False
        else:
            df_copy.loc[curr, 'in_uptrend'] = df_copy.loc[prev, 'in_uptrend']
            
        if df_copy.loc[curr, 'in_uptrend'] and df_copy.loc[curr, 'lowerband'] < df_copy.loc[prev, 'lowerband']:
            df_copy.loc[curr, 'lowerband'] = df_copy.loc[prev, 'lowerband']
        if not df_copy.loc[curr, 'in_uptrend'] and df_copy.loc[curr, 'upperband'] > df_copy.loc[prev, 'upperband']:
            df_copy.loc[curr, 'upperband'] = df_copy.loc[prev, 'upperband']
            
    return df_copy

def generate_technical_analysis_score(df: pd.DataFrame) -> Dict[str, Any]:
    """تمام تکنیکی انڈیکیٹرز کی بنیاد پر ایک مجموعی اسکور تیار کرتا ہے۔"""
    if len(df) < max(EMA_LONG_PERIOD, RSI_PERIOD, 34):
        return {"score": 0, "indicators": {}, "reason": "ناکافی ڈیٹا"}
        
    close = df['close']
    WEIGHTS = _load_weights()
    
    ema_fast = close.ewm(span=EMA_SHORT_PERIOD, adjust=False).mean()
    ema_slow = close.ewm(span=EMA_LONG_PERIOD, adjust=False).mean()
    rsi = calculate_rsi(close, RSI_PERIOD)
    stoch = calculate_stoch(df['high'], df['low'], close, STOCH_K, STOCH_D)
    df_supertrend = calculate_supertrend(df, SUPERTREND_ATR, SUPERTREND_FACTOR)
    
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
    بہترین TP/SL لیولز کا حساب لگاتا ہے اور ان کی منطقی حیثیت کو یقینی بناتا ہے۔
    """
    if df.empty or len(df) < 34:
        logger.warning("TP/SL کے حساب کے لیے ناکافی ڈیٹا۔")
        return None
    try:
        result = find_optimal_tp_sl(df, signal_type)
        
        # اصلاح: حتمی حفاظتی جانچ
        if result is None:
            return None

        tp, sl = result
        last_close = df['close'].iloc[-1]

        # یقینی بنائیں کہ TP/SL منطقی ہیں
        if signal_type == 'buy' and (tp <= last_close or sl >= last_close):
            logger.error(f"غیر منطقی TP/SL کا حساب لگایا گیا (Buy): TP={tp}, SL={sl}, Close={last_close}")
            return None
        if signal_type == 'sell' and (tp >= last_close or sl <= last_close):
            logger.error(f"غیر منطقی TP/SL کا حساب لگایا گیا (Sell): TP={tp}, SL={sl}, Close={last_close}")
            return None
            
        return result

    except Exception as e:
        logging.error(f"TP/SL کیلکولیشن میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        return None
    
