# filename: level_analyzer.py

import logging
from typing import Dict, Optional, Tuple

import pandas as pd
import numpy as np

from config import strategy_settings

logger = logging.getLogger(__name__)

# --- مستقل اقدار ---
MIN_RR_RATIO = strategy_settings.MIN_RISK_REWARD_RATIO

# --- نیا: ٹرینڈ فالوونگ کے لیے TP/SL فنکشن ---
def find_trend_tp_sl(
    df: pd.DataFrame, 
    signal_type: str, 
    symbol_personality: Dict
) -> Optional[Tuple[float, float]]:
    """
    ٹرینڈ فالوونگ سگنلز کے لیے حقیقت پسندانہ TP/SL کا تعین کرتا ہے۔
    SL حالیہ سوئنگ لو/ہائی پر مبنی ہے، اور TP ایک مقررہ رسک/ریوارڈ تناسب پر ہے۔
    """
    if len(df) < 20:
        logger.warning("ٹرینڈ TP/SL کے لیے ناکافی ڈیٹا۔")
        return None

    last_close = df['close'].iloc[-1]
    
    # SL کا تعین: حالیہ سوئنگ لو/ہائی
    if signal_type == 'buy':
        # حالیہ 20 کینڈلز کے سب سے نچلے پوائنٹ کو تلاش کریں
        swing_low = df['low'].tail(20).min()
        stop_loss = swing_low
    else:  # 'sell'
        # حالیہ 20 کینڈلز کے سب سے اونچے پوائنٹ کو تلاش کریں
        swing_high = df['high'].tail(20).max()
        stop_loss = swing_high

    # رسک کا حساب لگائیں
    risk = abs(last_close - stop_loss)
    if risk == 0:
        logger.warning("رسک صفر ہے، TP/SL کا حساب نہیں لگایا جا سکتا۔")
        return None

    # TP کا تعین: رسک/ریوارڈ تناسب کی بنیاد پر
    # شخصیت سے RR تناسب حاصل کریں، ورنہ ڈیفالٹ استعمال کریں
    rr_ratio = symbol_personality.get("min_rr_ratio", MIN_RR_RATIO)
    
    if signal_type == 'buy':
        take_profit = last_close + (risk * rr_ratio)
    else:  # 'sell'
        take_profit = last_close - (risk * rr_ratio)

    logger.info(f"ٹرینڈ TP/SL ملا: TP={take_profit:.5f}, SL={stop_loss:.5f} (RR: {rr_ratio})")
    return take_profit, stop_loss

# --- نیا: رینج ریورسل کے لیے TP/SL فنکشن ---
def find_reversal_tp_sl(
    df: pd.DataFrame, 
    signal_type: str, 
    symbol_personality: Dict,
    bb_window: int,
    bb_std: int
) -> Optional[Tuple[float, float]]:
    """
    رینج ریورسل سگنلز کے لیے بہترین TP/SL کا تعین کرتا ہے۔
    SL بولنگر بینڈ کے باہر ATR بفر کے ساتھ ہے، اور TP درمیانی بینڈ پر ہے۔
    """
    if len(df) < bb_window:
        logger.warning("ریورسل TP/SL کے لیے ناکافی ڈیٹا۔")
        return None

    close = df['close']
    
    # بولنگر بینڈز کا دوبارہ حساب لگائیں
    rolling_mean = close.rolling(window=bb_window).mean()
    rolling_std = close.rolling(window=bb_window).std()
    middle_band = rolling_mean.iloc[-1]
    
    # ATR کا حساب لگائیں
    tr = pd.concat([df['high'] - df['low'], abs(df['high'] - close.shift()), abs(df['low'] - close.shift())], axis=1).max(axis=1)
    atr = tr.ewm(span=14, adjust=False).mean().iloc[-1]
    
    last_close = close.iloc[-1]
    
    # شخصیت سے اتار چڑھاؤ کا ضرب حاصل کریں
    volatility_multiplier = symbol_personality.get("volatility_multiplier", 1.5)
    
    # SL کا تعین: ATR بفر کے ساتھ
    if signal_type == 'buy':
        # SL کو انٹری قیمت سے ATR کی دوری پر رکھیں
        stop_loss = last_close - (atr * volatility_multiplier)
    else:  # 'sell'
        stop_loss = last_close + (atr * volatility_multiplier)

    # TP کا تعین: درمیانی بولنگر بینڈ
    take_profit = middle_band
    
    # رسک/ریوارڈ تناسب کی تصدیق کریں
    try:
        reward = abs(take_profit - last_close)
        risk = abs(last_close - stop_loss)
        if risk == 0: return None
        
        rr_ratio = reward / risk
        # ریورسل کے لیے کم از کم 1.0 کا RR قابلِ قبول ہے
        if rr_ratio < 1.0:
            logger.warning(f"ریورسل زون کا رسک/ریوارڈ تناسب ({rr_ratio:.2f}) کم از کم (1.0) سے کم ہے، مسترد۔")
            return None
            
    except ZeroDivisionError:
        return None

    logger.info(f"ریورسل TP/SL ملا: TP={take_profit:.5f}, SL={stop_loss:.5f} (RR: {rr_ratio:.2f})")
    return take_profit, stop_loss
    
