# filename: strategy_scalper.py

import logging
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np

from config import tech_settings
from level_analyzer import find_realistic_tp_sl

logger = logging.getLogger(__name__)

# --- تکنیکی انڈیکیٹرز کے حساب کتاب کے فنکشنز ---
# (یہ فنکشنز پہلے سے موجود ہو سکتے ہیں، لیکن انہیں یہاں رکھنا کوڈ کو مکمل بناتا ہے)

def calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    delta = data.diff(1)
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))

def calculate_bollinger_bands(data: pd.Series, period: int, std_dev: int) -> pd.DataFrame:
    middle_band = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    return pd.DataFrame({'bb_upper': upper_band, 'bb_lower': lower_band})

def calculate_supertrend(df_in: pd.DataFrame, atr_period: int, multiplier: float) -> pd.Series:
    df = df_in.copy()
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
            
    return df['in_uptrend']

# --- حکمت عملی 1: پرسکون ٹرینڈ کے لیے ---
def run_trend_following_strategy(df_in: pd.DataFrame, symbol_personality: Dict) -> Dict[str, Any]:
    """یہ حکمت عملی مستحکم ٹرینڈز میں EMA کراس اور Supertrend کی بنیاد پر کام کرتی ہے۔"""
    symbol = df_in['symbol'].iloc[-1]
    logger.info(f"[{symbol}] حکمت عملی فعال: ٹرینڈ فالوونگ")
    
    if len(df_in) < tech_settings.EMA_LONG_PERIOD:
        return {"status": "no-signal", "reason": "ٹرینڈ فالوونگ کے لیے ناکافی ڈیٹا"}

    df = df_in.copy()
    close = df['close']
    df['ema_fast'] = close.ewm(span=tech_settings.EMA_SHORT_PERIOD, adjust=False).mean()
    df['ema_slow'] = close.ewm(span=tech_settings.EMA_LONG_PERIOD, adjust=False).mean()
    df['in_uptrend'] = calculate_supertrend(df, tech_settings.SUPERTREND_ATR, tech_settings.SUPERTREND_FACTOR)
    
    last = df.iloc[-1]
    core_signal = ""

    if last['ema_fast'] > last['ema_slow'] and last['in_uptrend']:
        core_signal = "buy"
    elif last['ema_fast'] < last['ema_slow'] and not last['in_uptrend']:
        core_signal = "sell"
    else:
        return {"status": "no-signal", "reason": "ٹرینڈ کی واضح سمت نہیں"}

    tp_sl_data = find_realistic_tp_sl(df, core_signal, symbol_personality, "trending")
    if not tp_sl_data:
        return {"status": "no-signal", "reason": "TP/SL کا حساب نہیں لگایا جا سکا"}
    
    tp, sl = tp_sl_data
    return {"status": "ok", "signal": core_signal, "price": last['close'], "tp": tp, "sl": sl, "strategy": "Trend_Following"}

# --- حکمت عملی 2: تنگ رینج کے لیے ---
def run_mean_reversion_strategy(df_in: pd.DataFrame, symbol_personality: Dict) -> Dict[str, Any]:
    """یہ حکمت عملی رینج کی بیرونی حدود سے قیمت کے واپس پلٹنے پر ٹریڈ کرتی ہے۔"""
    symbol = df_in['symbol'].iloc[-1]
    logger.info(f"[{symbol}] حکمت عملی فعال: مین ریورژن")
    
    if len(df_in) < tech_settings.BBANDS_PERIOD:
        return {"status": "no-signal", "reason": "مین ریورژن کے لیے ناکافی ڈیٹا"}

    df = df_in.copy()
    close = df['close']
    df = df.join(calculate_bollinger_bands(close, tech_settings.BBANDS_PERIOD, tech_settings.BBANDS_STD_DEV))
    df['rsi'] = calculate_rsi(close, tech_settings.RSI_PERIOD)
    
    last = df.iloc[-1]
    core_signal = ""

    if last['rsi'] < 30 and last['close'] <= last['bb_lower']:
        core_signal = "buy"
    elif last['rsi'] > 70 and last['close'] >= last['bb_upper']:
        core_signal = "sell"
    else:
        return {"status": "no-signal", "reason": "کوئی اوور سولڈ/اوور باٹ حالت نہیں"}

    tp_sl_data = find_realistic_tp_sl(df, core_signal, symbol_personality, "ranging")
    if not tp_sl_data:
        return {"status": "no-signal", "reason": "TP/SL کا حساب نہیں لگایا جا سکا"}
    
    tp, sl = tp_sl_data
    return {"status": "ok", "signal": core_signal, "price": last['close'], "tp": tp, "sl": sl, "strategy": "Mean_Reversion"}

# --- حکمت عملی 3: دھماکہ خیز ٹرینڈ کے لیے ---
def run_breakout_strategy(df_in: pd.DataFrame, symbol_personality: Dict) -> Dict[str, Any]:
    """یہ حکمت عملی قیمت کے ایک اہم سطح (Donchian Channel) کو توڑنے پر ٹریڈ کرتی ہے۔"""
    symbol = df_in['symbol'].iloc[-1]
    logger.info(f"[{symbol}] حکمت عملی فعال: بریک آؤٹ")
    
    df = df_in.copy()
    df['donchian_high'] = df['high'].rolling(tech_settings.BBANDS_PERIOD).max().shift(1)
    df['donchian_low'] = df['low'].rolling(tech_settings.BBANDS_PERIOD).min().shift(1)
    
    last = df.iloc[-1]
    core_signal = ""

    if pd.isna(last['donchian_high']) or pd.isna(last['donchian_low']):
        return {"status": "no-signal", "reason": "بریک آؤٹ سطحوں کا حساب لگانے کے لیے ناکافی ڈیٹا"}

    if last['close'] > last['donchian_high']:
        core_signal = "buy"
    elif last['close'] < last['donchian_low']:
        core_signal = "sell"
    else:
        return {"status": "no-signal", "reason": "کوئی بریک آؤٹ نہیں"}

    tp_sl_data = find_realistic_tp_sl(df, core_signal, symbol_personality, "trending")
    if not tp_sl_data:
        return {"status": "no-signal", "reason": "TP/SL کا حساب نہیں لگایا جا سکا"}
    
    tp, sl = tp_sl_data
    return {"status": "ok", "signal": core_signal, "price": last['close'], "tp": tp, "sl": sl, "strategy": "Breakout"}
    
