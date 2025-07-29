# filename: strategybot.py

import pandas as pd
import numpy as np
import json
import logging
from typing import List, Tuple, Optional, Dict, Any

from level_analyzer import find_optimal_tp_sl

logger = logging.getLogger(__name__)
WEIGHTS_FILE = "strategy_weights.json"

# --- حکمت عملی کے پیرامیٹرز ---
EMA_SHORT_PERIOD = 10
EMA_LONG_PERIOD = 30
RSI_PERIOD = 14
STOCH_K = 14
STOCH_D = 3
SUPERTREND_ATR = 10
SUPERTREND_FACTOR = 3.0

def _load_weights() -> Dict[str, float]:
    """JSON فائل سے حکمت عملی کے وزن کو لوڈ کرتا ہے۔"""
    try:
        with open(WEIGHTS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning(f"{WEIGHTS_FILE} نہیں ملی یا خراب ہے۔ ڈیفالٹ وزن استعمال کیا جا رہا ہے۔")
        return {
            "ema_cross": 0.30, "rsi_position": 0.20, "stoch_position": 0.20,
            "price_action": 0.10, "supertrend_confirm": 0.20
        }

# ★★★ نیا: ATR پر مبنی متبادل TP/SL کا حساب لگانے کا فنکشن ★★★
def _calculate_atr_fallback_tp_sl(df: pd.DataFrame, signal_type: str) -> Optional[Tuple[float, float]]:
    """ATR کی بنیاد پر ایک محفوظ متبادل TP/SL کا حساب لگاتا ہے۔"""
    try:
        # ATR کا حساب (riskguardian.py سے منطق لی گئی)
        df['h-l'] = df['high'] - df['low']
        df['h-pc'] = np.abs(df['high'] - df['close'].shift())
        df['l-pc'] = np.abs(df['low'] - df['close'].shift())
        tr = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
        atr = tr.rolling(window=14).mean()
        
        if atr.empty or pd.isna(atr.iloc[-1]):
            logger.error("ATR کا حساب نہیں لگایا جا سکا، متبادل TP/SL ناکام۔")
            return None

        last_close = df['close'].iloc[-1]
        current_atr = atr.iloc[-1]
        
        # رسک/ریوارڈ 1:2 کے ساتھ
        if signal_type == 'buy':
            sl = last_close - (1.5 * current_atr)
            tp = last_close + (3.0 * current_atr)
        else: # sell
            sl = last_close + (1.5 * current_atr)
            tp = last_close - (3.0 * current_atr)
        
        logger.info(f"ATR پر مبنی متبادل TP/SL: TP={tp:.5f}, SL={sl:.5f}")
        return tp, sl
    except Exception as e:
        logger.error(f"ATR متبادل TP/SL کیلکولیشن میں خرابی: {e}", exc_info=True)
        return None

# ★★★ اپ ڈیٹ شدہ مرکزی فنکشن ★★★
def calculate_tp_sl(candles: List[Dict], signal_type: str) -> Optional[Tuple[float, float]]:
    """
    بہترین TP/SL لیولز کی شناخت کرتا ہے، جس میں کنفلونس کو ترجیح دی جاتی ہے
    اور ATR کو متبادل کے طور پر استعمال کیا جاتا ہے۔
    """
    if not candles or len(candles) < 34:
        logger.warning("TP/SL کیلکولیشن کے لیے ناکافی کینڈل ڈیٹا۔")
        return None
        
    try:
        # پہلی ترجیح: کنفلونس پر مبنی لیولز
        optimal_levels = find_optimal_tp_sl(candles, signal_type)
        if optimal_levels:
            logger.info("بہترین TP/SL کنفلونس کی بنیاد پر ملا۔")
            return optimal_levels

        # متبادل: ATR پر مبنی TP/SL
        logger.warning("کنفلونس لیولز نہیں ملے۔ ATR پر مبنی متبادل TP/SL کا حساب لگایا جا رہا ہے۔")
        df = pd.DataFrame(candles)
        # ڈیٹا کی اقسام کو یقینی بنائیں
        for col in ['high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=['high', 'low', 'close'], inplace=True)
        
        return _calculate_atr_fallback_tp_sl(df, signal_type)

    except Exception as e:
        logging.error(f"TP/SL کیلکولیشن میں خرابی: {e}", exc_info=True)
        return None

# --- انڈیکیٹر کیلکولیشن فنکشنز (کوئی تبدیلی نہیں) ---
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

def calculate_supertrend(df: pd.DataFrame, atr_period: int, multiplier: float) -> pd.DataFrame:
    high, low, close = df['high'], df['low'], df['close']
    hl2 = (high + low) / 2
    df['atr'] = (high - low).abs().rolling(window=atr_period).mean()
    df['upperband'] = hl2 + (multiplier * df['atr'])
    df['lowerband'] = hl2 - (multiplier * df['atr'])
    df['in_uptrend'] = True
    for i in range(1, len(df)):
        if close.iloc[i] > df['upperband'].iloc[i-1]:
            df.loc[df.index[i], 'in_uptrend'] = True
        elif close.iloc[i] < df['lowerband'].iloc[i-1]:
            df.loc[df.index[i], 'in_uptrend'] = False
        else:
            df.loc[df.index[i], 'in_uptrend'] = df['in_uptrend'].iloc[i-1]
            if df['in_uptrend'].iloc[i] and df['lowerband'].iloc[i] < df['lowerband'].iloc[i-1]:
                df.loc[df.index[i], 'lowerband'] = df['lowerband'].iloc[i-1]
            if not df['in_uptrend'].iloc[i] and df['upperband'].iloc[i] > df['upperband'].iloc[i-1]:
                df.loc[df.index[i], 'upperband'] = df['upperband'].iloc[i-1]
    return df

# --- بنیادی حکمت عملی کا اسکور پیدا کرنے والا فنکشن (کوئی تبدیلی نہیں) ---
def generate_technical_analysis_score(candles: List[Dict]) -> Dict[str, Any]:
    if len(candles) < max(EMA_LONG_PERIOD, RSI_PERIOD, 34):
        return {"score": 0, "indicators": {}, "reason": "ناکافی ڈیٹا"}

    df = pd.DataFrame(candles)
    close = df['close']
    
    WEIGHTS = _load_weights()
    
    ema_fast = close.ewm(span=EMA_SHORT_PERIOD, adjust=False).mean()
    ema_slow = close.ewm(span=EMA_LONG_PERIOD, adjust=False).mean()
    rsi = calculate_rsi(close, RSI_PERIOD)
    stoch = calculate_stoch(df['high'], df['low'], close, STOCH_K, STOCH_D)
    df = calculate_supertrend(df, SUPERTREND_ATR, SUPERTREND_FACTOR)
    
    last_ema_fast, last_ema_slow = ema_fast.iloc[-1], ema_slow.iloc[-1]
    last_rsi, last_stoch_k = rsi.iloc[-1], stoch['STOCHk'].iloc[-1]
    last_close, prev_close = close.iloc[-1], close.iloc[-2]
    in_uptrend = df['in_uptrend'].iloc[-1]

    if any(pd.isna(v) for v in [last_ema_fast, last_ema_slow, last_rsi, last_stoch_k]):
        return {"score": 0, "indicators": {}, "reason": "انڈیکیٹر کیلکولیشن میں خرابی"}

    ema_score = 1 if last_ema_fast > last_ema_slow else -1
    rsi_score = 1 if last_rsi > 52 else (-1 if last_rsi < 48 else 0)
    stoch_score = 1 if last_stoch_k > 50 else -1
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
    
