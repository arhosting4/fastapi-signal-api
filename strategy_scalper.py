# filename: strategy_scalper.py

import logging
from typing import Any, Dict, Optional

import pandas as pd
import numpy as np

from config import tech_settings
from level_analyzer import find_realistic_tp_sl

logger = logging.getLogger(__name__)

# --- تکنیکی انڈیکیٹرز کی سیٹنگز ---
EMA_SHORT_PERIOD = tech_settings.EMA_SHORT_PERIOD
EMA_LONG_PERIOD = tech_settings.EMA_LONG_PERIOD
RSI_PERIOD = tech_settings.RSI_PERIOD
SUPERTREND_ATR = tech_settings.SUPERTREND_ATR
SUPERTREND_FACTOR = tech_settings.SUPERTREND_FACTOR
BBANDS_PERIOD = tech_settings.BBANDS_PERIOD
BBANDS_STD_DEV = tech_settings.BBANDS_STD_DEV
BBANDS_SQUEEZE_THRESHOLD = tech_settings.BBANDS_SQUEEZE_THRESHOLD

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

def calculate_bollinger_bands(data: pd.Series, period: int, std_dev: int) -> pd.DataFrame:
    """بولنگر بینڈز اور بینڈ کی چوڑائی کا حساب لگاتا ہے۔"""
    middle_band = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    
    # بینڈ کی چوڑائی (Bandwidth) کا حساب لگائیں
    bandwidth = ((upper_band - lower_band) / middle_band) * 100
    
    return pd.DataFrame({
        'bb_upper': upper_band,
        'bb_middle': middle_band,
        'bb_lower': lower_band,
        'bb_bandwidth': bandwidth
    })

def generate_adaptive_analysis(df: pd.DataFrame, market_regime: Dict, symbol_personality: Dict) -> Dict[str, Any]:
    regime_type = market_regime.get("regime")
    
    if len(df) < max(EMA_LONG_PERIOD, RSI_PERIOD, BBANDS_PERIOD, 34):
        return {"status": "no-signal", "reason": "ناکافی ڈیٹا"}

    close = df['close']
    
    # --- تمام انڈیکیٹرز کا حساب لگائیں ---
    ema_fast = close.ewm(span=EMA_SHORT_PERIOD, adjust=False).mean()
    ema_slow = close.ewm(span=EMA_LONG_PERIOD, adjust=False).mean()
    rsi = calculate_rsi(close, RSI_PERIOD)
    df_supertrend = calculate_supertrend(df.copy(), SUPERTREND_ATR, SUPERTREND_FACTOR)
    df_bbands = calculate_bollinger_bands(close, BBANDS_PERIOD, BBANDS_STD_DEV)
    df = df.join(df_bbands)

    # آخری کینڈل کا ڈیٹا
    last_candle = df.iloc[-1]
    prev_candle = df.iloc[-2]

    # --- حکمت عملی 1: بریک آؤٹ ہنٹر (سب سے زیادہ ترجیح) ---
    # کیا بولنگر بینڈز "Squeeze" میں ہیں؟ (یعنی بینڈ کی چوڑائی بہت کم ہے)
    is_squeeze = last_candle['bb_bandwidth'] < BBANDS_SQUEEZE_THRESHOLD
    
    if is_squeeze:
        logger.info(f"[{df['symbol'].iloc[-1]}] بولنگر بینڈ Squeeze میں ہے۔ بریک آؤٹ کا انتظار ہے۔ Bandwidth: {last_candle['bb_bandwidth']:.2f}%")
        
        # Buy Breakout: قیمت اوپری بینڈ کے اوپر بند ہوئی
        if last_candle['close'] > last_candle['bb_upper'] and prev_candle['close'] < prev_candle['bb_upper']:
            logger.info(f"[{df['symbol'].iloc[-1]}] Bullish Breakout کی تصدیق!")
            core_signal = "buy"
            strategy_type = "Breakout-Hunter"
            total_score = 100 # بریک آؤٹ کو اعلی اسکور دیں
            
            tp_sl_data = find_realistic_tp_sl(df, core_signal, symbol_personality)
            if tp_sl_data:
                tp, sl = tp_sl_data
                return {
                    "status": "ok", "signal": core_signal, "score": total_score,
                    "price": last_candle['close'], "tp": tp, "sl": sl,
                    "strategy_type": strategy_type
                }

        # Sell Breakout: قیمت نچلے بینڈ کے نیچے بند ہوئی
        elif last_candle['close'] < last_candle['bb_lower'] and prev_candle['close'] > prev_candle['bb_lower']:
            logger.info(f"[{df['symbol'].iloc[-1]}] Bearish Breakout کی تصدیق!")
            core_signal = "sell"
            strategy_type = "Breakout-Hunter"
            total_score = -100
            
            tp_sl_data = find_realistic_tp_sl(df, core_signal, symbol_personality)
            if tp_sl_data:
                tp, sl = tp_sl_data
                return {
                    "status": "ok", "signal": core_signal, "score": total_score,
                    "price": last_candle['close'], "tp": tp, "sl": sl,
                    "strategy_type": strategy_type
                }

    # --- حکمت عملی 2: ٹرینڈ فالوونگ / رینج ریورسل (اگر بریک آؤٹ نہیں ہے) ---
    total_score = 0
    strategy_type = "Unknown"

    if regime_type in ["Calm Trend", "Volatile Trend"]:
        strategy_type = "Trend-Following"
        ema_score = 1 if ema_fast.iloc[-1] > ema_slow.iloc[-1] else -1
        supertrend_score = 1 if df_supertrend['in_uptrend'].iloc[-1] else -1
        total_score = (ema_score * 0.5) + (supertrend_score * 0.5)
        total_score *= 100
    
    elif regime_type == "Ranging":
        strategy_type = "Range-Reversal"
        if rsi.iloc[-1] > 70: total_score = -100
        elif rsi.iloc[-1] < 30: total_score = 100
    
    else:
        return {"status": "no-signal", "reason": f"مارکیٹ کا نظام '{regime_type}' ہے۔ ٹریڈنگ معطل۔"}

    if abs(total_score) < 35:
        return {"status": "no-signal", "reason": f"تکنیکی اسکور ({total_score:.1f}) تھریشولڈ سے کم ہے۔"}

    core_signal = "buy" if total_score > 0 else "sell"
    
    tp_sl_data = find_realistic_tp_sl(df, core_signal, symbol_personality)
    if not tp_sl_data:
        return {"status": "no-signal", "reason": "حقیقت پسندانہ TP/SL کا حساب نہیں لگایا جا سکا"}

    tp, sl = tp_sl_data
    
    return {
        "status": "ok",
        "signal": core_signal,
        "score": total_score,
        "price": last_candle['close'],
        "tp": tp,
        "sl": sl,
        "strategy_type": strategy_type
            }
        
