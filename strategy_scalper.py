# filename: strategy_scalper.py

import json
import logging
from typing import Any, Dict, Optional

import pandas as pd

# اب ہم level_analyzer سے دونوں فنکشنز درآمد کریں گے
from level_analyzer import find_trend_tp_sl, find_reversal_tp_sl
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

# --- وزن لوڈ کرنے کا فنکشن ---
def _load_weights() -> Dict[str, float]:
    try:
        with open(WEIGHTS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning(f"{WEIGHTS_FILE} نہیں ملی یا خراب ہے۔ ڈیفالٹ وزن استعمال کیا جا رہا ہے۔")
        # اب ہم ریورسل کے لیے بھی وزن شامل کریں گے
        return {
            "ema_cross": 0.25, "rsi_position": 0.15, "price_action": 0.10,
            "supertrend_confirm": 0.25, "bollinger_touch": 0.15, "stoch_reversal": 0.10
        }

# --- انڈیکیٹر کیلکولیشن فنکشنز (کوئی تبدیلی نہیں) ---
def calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    delta = data.diff(1)
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def calculate_stoch(high: pd.Series, low: pd.Series, close: pd.Series, k: int, d: int) -> pd.DataFrame:
    low_k = low.rolling(window=k).min()
    high_k = high.rolling(window=k).max()
    stoch_k = 100 * (close - low_k) / (high_k - low_k).replace(0, 1e-9)
    stoch_d = stoch_k.rolling(window=d).mean()
    stoch_df = pd.DataFrame({'STOCHk': stoch_k, 'STOCHd': stoch_d})
    return stoch_df.fillna(50)

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

# --- نیا مرکزی فنکشن ---
def generate_adaptive_analysis(df: pd.DataFrame, market_regime: str, symbol_personality: Dict) -> Dict[str, Any]:
    """
    مارکیٹ کے نظام کی بنیاد پر انکولی تکنیکی تجزیہ کرتا ہے۔
    یہ صحیح حکمت عملی (ٹرینڈ یا ریورسل) کا انتخاب کرتا ہے۔
    """
    if len(df) < max(EMA_LONG_PERIOD, RSI_PERIOD, 34):
        return {"status": "no-signal", "reason": "ناکافی ڈیٹا"}

    # اگر مارکیٹ خطرناک ہے تو فوراً باہر نکل جائیں
    if market_regime == "Kill Zone":
        return {"status": "no-signal", "reason": "مارکیٹ کا نظام 'Kill Zone' ہے۔ ٹریڈنگ معطل۔"}

    # مارکیٹ کے نظام کی بنیاد پر صحیح تجزیاتی فنکشن کو کال کریں
    if market_regime in ["Calm Trend", "Volatile Trend"]:
        logger.info(f"حکمت عملی منتخب: ٹرینڈ فالوونگ (نظام: {market_regime})")
        return _analyze_trend_following(df, symbol_personality)
    elif market_regime == "Calm Range":
        logger.info(f"حکمت عملی منتخب: رینج ریورسل (نظام: {market_regime})")
        return _analyze_range_reversal(df, symbol_personality)
    else:
        return {"status": "no-signal", "reason": f"نامعلوم مارکیٹ نظام: {market_regime}"}

# --- ٹرینڈ فالوونگ حکمت عملی ---
def _analyze_trend_following(df: pd.DataFrame, symbol_personality: Dict) -> Dict[str, Any]:
    """ٹرینڈ والی مارکیٹ کے لیے تکنیکی تجزیہ کرتا ہے۔"""
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
    
    ema_score = 1 if last_ema_fast > last_ema_slow else -1
    rsi_score = 1 if last_rsi > 55 else (-1 if last_rsi < 45 else 0) # ٹرینڈ کے لیے سخت شرائط
    price_action_score = 1 if last_close > prev_close else -1
    supertrend_score = 1 if in_uptrend else -1
    
    total_score = (
        (ema_score * WEIGHTS.get("ema_cross", 0.25)) +
        (rsi_score * WEIGHTS.get("rsi_position", 0.15)) +
        (price_action_score * WEIGHTS.get("price_action", 0.10)) +
        (supertrend_score * WEIGHTS.get("supertrend_confirm", 0.25))
    ) * 100
    
    core_signal = "wait"
    if total_score > 40: core_signal = "buy"
    elif total_score < -40: core_signal = "sell"

    if core_signal == "wait":
        return {"status": "no-signal", "reason": f"ٹرینڈ اسکور ({total_score:.2f}) تھریشولڈ سے کم ہے۔"}

    # ٹرینڈ کے لیے صحیح TP/SL فنکشن کو کال کریں
    tp_sl_data = find_trend_tp_sl(df, core_signal, symbol_personality)
    if not tp_sl_data:
        return {"status": "no-signal", "reason": "بہترین ٹرینڈ TP/SL کا حساب نہیں لگایا جا سکا"}
    tp, sl = tp_sl_data
    
    return {
        "status": "ok", "signal": core_signal, "price": last_close, "tp": tp, "sl": sl,
        "score": total_score, "strategy_type": "Trend-Following"
    }

# --- رینج ریورسل حکمت عملی ---
def _analyze_range_reversal(df: pd.DataFrame, symbol_personality: Dict) -> Dict[str, Any]:
    """رینج والی مارکیٹ کے لیے ریورسل تجزیہ کرتا ہے۔"""
    close = df['close']
    WEIGHTS = _load_weights()
    
    # بولنگر بینڈز
    bb_window = 20
    bb_std = 2
    rolling_mean = close.rolling(window=bb_window).mean()
    rolling_std = close.rolling(window=bb_window).std()
    upper_band = rolling_mean + (rolling_std * bb_std)
    lower_band = rolling_mean - (rolling_std * bb_std)
    
    # Stochastic
    stoch = calculate_stoch(df['high'], df['low'], close, STOCH_K, STOCH_D)
    
    last_close = close.iloc[-1]
    last_upper_band = upper_band.iloc[-1]
    last_lower_band = lower_band.iloc[-1]
    last_stoch_k = stoch['STOCHk'].iloc[-1]

    if any(pd.isna(v) for v in [last_upper_band, last_lower_band, last_stoch_k]):
        return {"status": "no-signal", "reason": "ریورسل انڈیکیٹرز میں خرابی"}

    buy_signal = last_close <= last_lower_band and last_stoch_k < 20
    sell_signal = last_close >= last_upper_band and last_stoch_k > 80
    
    core_signal = "wait"
    if buy_signal: core_signal = "buy"
    elif sell_signal: core_signal = "sell"

    if core_signal == "wait":
        return {"status": "no-signal", "reason": "کوئی ریورسل سیٹ اپ نہیں ملا۔"}

    # ریورسل کے لیے صحیح TP/SL فنکشن کو کال کریں
    tp_sl_data = find_reversal_tp_sl(df, core_signal, symbol_personality, bb_window, bb_std)
    if not tp_sl_data:
        return {"status": "no-signal", "reason": "بہترین ریورسل TP/SL کا حساب نہیں لگایا جا سکا"}
    tp, sl = tp_sl_data

    # ریورسل کے لیے اسکور کا حساب
    score = 70 + (abs(50 - last_stoch_k) / 50 * 30) # بنیادی اسکور 70، اسٹاکسٹک کی شدت پر منحصر

    return {
        "status": "ok", "signal": core_signal, "price": last_close, "tp": tp, "sl": sl,
        "score": score, "strategy_type": "Range-Reversal"
    }
    
