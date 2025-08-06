import json
import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

# ★★★ تبدیلی یہاں ہے ★★★
# پرانے فنکشن کی جگہ نیا فنکشن امپورٹ کریں
from level_analyzer import find_intelligent_range_tp_sl
from config import tech_settings

logger = logging.getLogger(__name__)
WEIGHTS_FILE = "strategy_weights.json"

# --- کنفیگریشن سے پیرامیٹرز ---
EMA_SHORT_PERIOD = tech_settings.EMA_SHORT_PERIOD
EMA_LONG_PERIOD = tech_settings.EMA_LONG_PERIOD
RSI_PERIOD = tech_settings.RSI_PERIOD
SUPERTREND_ATR = tech_settings.SUPERTREND_ATR
SUPERTREND_FACTOR = tech_settings.SUPERTREND_FACTOR

def _load_weights() -> Dict[str, float]:
    try:
        with open(WEIGHTS_FILE, 'r') as f:
            weights = json.load(f)
            weights.pop("stoch_position", None)
            total_weight = sum(weights.values())
            if total_weight > 0:
                return {key: value / total_weight for key, value in weights.items()}
            return weights
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning(f"{WEIGHTS_FILE} نہیں ملی یا خراب ہے۔ ڈیفالٹ وزن استعمال کیا جا رہا ہے۔")
        return {
            "ema_cross": 0.40, 
            "rsi_position": 0.30,
            "price_action": 0.10, 
            "supertrend_confirm": 0.20
        }

def calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    delta = data.diff(1)
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def calculate_supertrend(df: pd.DataFrame, atr_period: int, multiplier: float) -> pd.DataFrame:
    high, low, close = df['high'], df['low'], df['close']
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)
    atr = tr.ewm(alpha=1/atr_period, adjust=False).mean()
    df['upperband'] = (high + low) / 2 + (multiplier * atr)
    df['lowerband'] = (high + low) / 2 - (multiplier * atr)
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

def generate_scalping_analysis(df: pd.DataFrame, symbol_personality: Dict, market_regime: Dict) -> Dict[str, Any]:
    if len(df) < max(EMA_LONG_PERIOD, RSI_PERIOD, 50): # کم از کم 50 کینڈلز کی ضرورت
        return {"score": 0, "indicators": {}, "reason": "ناکافی ڈیٹا"}
    
    close = df['close']
    WEIGHTS = _load_weights()
    ema_fast = close.ewm(span=EMA_SHORT_PERIOD, adjust=False).mean()
    ema_slow = close.ewm(span=EMA_LONG_PERIOD, adjust=False).mean()
    rsi = calculate_rsi(close, RSI_PERIOD)
    df_supertrend = calculate_supertrend(df.copy(), SUPERTREND_ATR, SUPERTREND_FACTOR)
    
    last_ema_fast, last_ema_slow = ema_fast.iloc[-1], ema_slow.iloc[-1]
    last_rsi = rsi.iloc[-1]
    last_close, prev_close = close.iloc[-1], close.iloc[-2]
    in_uptrend = df_supertrend['in_uptrend'].iloc[-1]
    
    if any(pd.isna(v) for v in [last_ema_fast, last_ema_slow, last_rsi]):
        return {"score": 0, "indicators": {}, "reason": "انڈیکیٹر کیلکولیشن میں خرابی"}
        
    ema_score = 1 if last_ema_fast > last_ema_slow else -1
    rsi_score = 1 if last_rsi > 52 else (-1 if last_rsi < 48 else 0)
    price_action_score = 1 if last_close > prev_close else -1
    supertrend_score = 1 if in_uptrend else -1
    
    total_score = (
        (ema_score * WEIGHTS.get("ema_cross", 0.40)) +
        (rsi_score * WEIGHTS.get("rsi_position", 0.30)) +
        (price_action_score * WEIGHTS.get("price_action", 0.10)) +
        (supertrend_score * WEIGHTS.get("supertrend_confirm", 0.20))
    ) * 100
    
    core_signal = "wait"
    score_threshold = 45 if market_regime['regime'] == 'Volatile' else 40

    if total_score > score_threshold: core_signal = "buy"
    elif total_score < -score_threshold: core_signal = "sell"

    if core_signal == "wait":
        return {"status": "no-signal", "reason": f"تکنیکی اسکور ({total_score:.2f}) مطلوبہ حد ({score_threshold}) سے کم ہے۔"}

    # ★★★ تبدیلی یہاں ہے ★★★
    # نئے ذہین فنکشن کو کال کریں
    tp_sl_data = find_intelligent_range_tp_sl(df, core_signal, symbol_personality)
    if not tp_sl_data:
        return {"status": "no-signal", "reason": "بہترین TP/SL رینج کا حساب نہیں لگایا جا سکا"}

    tp, sl = tp_sl_data
    
    indicators_data = {
        "ema_fast": round(last_ema_fast, 5), "ema_slow": round(last_ema_slow, 5),
        "rsi": round(last_rsi, 2),
        "supertrend_direction": "Up" if in_uptrend else "Down",
        "technical_score": round(total_score, 2),
        "component_scores": {
            "ema_cross": ema_score, "rsi_position": rsi_score,
            "price_action": price_action_score,
            "supertrend_confirm": supertrend_score
        }
    }
    
    return {
        "status": "ok",
        "signal": core_signal,
        "score": total_score,
        "price": last_close,
        "tp": tp,
        "sl": sl,
        "indicators": indicators_data
    }
    
