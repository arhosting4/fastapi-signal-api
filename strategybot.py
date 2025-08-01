# filename: strategybot.py

import pandas as pd
import numpy as np
import json
import logging
from typing import List, Tuple, Optional, Dict, Any

# مقامی امپورٹس
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

# --- حکمت عملی کے وزن کو JSON فائل سے لوڈ کرتا ہے ---
def _load_weights() -> Dict[str, float]:
    try:
        with open(WEIGHTS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning(f"{WEIGHTS_FILE} نہیں ملی یا خراب ہے۔ ڈیفالٹ وزن استعمال کیا جا رہا ہے۔")
        return {
            "ema_cross": 0.30,
            "rsi_position": 0.20,
            "stoch_position": 0.20,
            "price_action": 0.10,
            "supertrend_confirm": 0.20
        }

# --- RSI کیلکولیٹ کرتا ہے ---
def calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    delta = data.diff()
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# --- EMA کیلکولیٹ ---
def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    return data.ewm(span=period, adjust=False).mean()

# --- اسٹاکاسٹک کیلکولیٹ ---
def calculate_stochastic(df: pd.DataFrame, k_period: int, d_period: int) -> Tuple[pd.Series, pd.Series]:
    low_min = df['low'].rolling(window=k_period).min()
    high_max = df['high'].rolling(window=k_period).max()
    k = 100 * ((df['close'] - low_min) / (high_max - low_min))
    d = k.rolling(window=d_period).mean()
    return k, d

# --- کور اسکور کیلکولیٹ فنکشن ---
def compute_core_score(df: pd.DataFrame) -> float:
    weights = _load_weights()

    ema_short = calculate_ema(df['close'], EMA_SHORT_PERIOD)
    ema_long = calculate_ema(df['close'], EMA_LONG_PERIOD)
    rsi = calculate_rsi(df['close'], RSI_PERIOD)
    k, d = calculate_stochastic(df, STOCH_K, STOCH_D)

    score = 0.0
    latest_idx = -1

    if ema_short.iloc[latest_idx] > ema_long.iloc[latest_idx]:
        score += weights["ema_cross"]

    if rsi.iloc[latest_idx] > 50:
        score += weights["rsi_position"]

    if k.iloc[latest_idx] > d.iloc[latest_idx]:
        score += weights["stoch_position"]

    # Price action + Supertrend placeholders
    score += weights["price_action"]  # future logic placeholder
    score += weights["supertrend_confirm"]  # future logic placeholder

    return round(score, 3)

# --- مین فنکشن: سگنل ریٹرن کرتا ہے ---
def generate_trade_signal(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty or len(df) < max(EMA_LONG_PERIOD, RSI_PERIOD, STOCH_K):
        return {"error": "ڈیٹا ناکافی ہے۔"}

    score = compute_core_score(df)
    tp_sl = find_optimal_tp_sl(df)

    return {
        "core_score": score,
        "tp": tp_sl.get("tp"),
        "sl": tp_sl.get("sl"),
        "confidence": round(min(score * 100, 100), 1),
        "strategy": "EMA + RSI + Stoch Combo"
        }
