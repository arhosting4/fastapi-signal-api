import logging
from typing import Dict, Optional, Tuple

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def _find_significant_swings(df: pd.DataFrame, window: int = 50) -> Dict[str, float]:
    """
    فراہم کردہ ونڈو میں سب سے نمایاں سوئنگ ہائی اور لو کو تلاش کرتا ہے۔
    """
    recent_data = df.tail(window)
    significant_high = recent_data['high'].max()
    significant_low = recent_data['low'].min()
    
    return {"high": significant_high, "low": significant_low}

def find_market_structure(df: pd.DataFrame, window: int = 20) -> Dict[str, str]:
    """
    مارکیٹ کی ساخت (اوپر/نیچے کا رجحان یا رینجنگ) کا تعین کرتا ہے۔
    (اس فنکشن میں کوئی تبدیلی نہیں کی گئی)
    """
    if len(df) < window:
        return {"trend": "غیر متعین", "reason": "ناکافی ڈیٹا۔"}
    
    df_copy = df.copy()
    df_copy['swing_high'] = df_copy['high'][(df_copy['high'].shift(1) < df_copy['high']) & (df_copy['high'].shift(-1) < df_copy['high'])]
    df_copy['swing_low'] = df_copy['low'][(df_copy['low'].shift(1) > df_copy['low']) & (df_copy['low'].shift(-1) > df_copy['low'])]
    
    recent_highs = df_copy['swing_high'].dropna().tail(2).values
    recent_lows = df_copy['swing_low'].dropna().tail(2).values
    
    if len(recent_highs) < 2 or len(recent_lows) < 2:
        return {"trend": "رینجنگ", "reason": "کوئی واضح سوئنگ پوائنٹس نہیں"}
        
    trend = "رینجنگ"
    if recent_highs[-1] > recent_highs[-2] and recent_lows[-1] > recent_lows[-2]:
        trend = "اوپر کا رجحان"
    elif recent_highs[-1] < recent_highs[-2] and recent_lows[-1] < recent_lows[-2]:
        trend = "نیچے کا رجحان"
        
    return {"trend": trend, "reason": f"مارکیٹ کی ساخت {trend} کی نشاندہی کرتی ہے۔"}

def find_intelligent_range_tp_sl(df: pd.DataFrame, signal_type: str, symbol_personality: Dict) -> Optional[Tuple[float, float]]:
    """
    ایک ذہین تجارتی رینج کی بنیاد پر TP/SL کا تعین کرتا ہے۔
    """
    if len(df) < 50:  # نمایاں سوئنگ کے لیے کم از کم 50 کینڈلز کی ضرورت ہے
        logger.warning("نمایاں سوئنگ لیولز تلاش کرنے کے لیے ناکافی ڈیٹا۔")
        return None
    
    last_close = df['close'].iloc[-1]
    
    # 1. نمایاں سوئنگ پوائنٹس کی شناخت کریں
    swings = _find_significant_swings(df, window=50)
    trading_range_high = swings['high']
    trading_range_low = swings['low']

    # 2. ATR کا حساب لگائیں
    tr = pd.concat([df['high'] - df['low'], abs(df['high'] - df['close'].shift()), abs(df['low'] - df['close'].shift())], axis=1).max(axis=1)
    atr = tr.ewm(span=14, adjust=False).mean().iloc[-1]
    
    if atr == 0:
        logger.warning("ATR صفر ہے، TP/SL کا حساب نہیں لگایا جا سکتا۔")
        return None

    # اثاثہ کی شخصیت سے پیرامیٹرز حاصل کریں
    sl_atr_multiplier = symbol_personality.get("volatility_multiplier", 1.5)
    min_rr_ratio = symbol_personality.get("min_rr_ratio", 1.5)

    # 3. TP اور SL کا ذہین تعین
    take_profit, stop_loss = None, None

    if signal_type == 'buy':
        # TP: تجارتی رینج کے اوپری حصے سے تھوڑا پہلے
        take_profit = trading_range_high - (atr * 0.2)
        # SL: تجارتی رینج کے نچلے حصے سے تھوڑا نیچے
        stop_loss = trading_range_low - (atr * sl_atr_multiplier)
    
    elif signal_type == 'sell':
        # TP: تجارتی رینج کے نچلے حصے سے تھوڑا پہلے
        take_profit = trading_range_low + (atr * 0.2)
        # SL: تجارتی رینج کے اوپری حصے سے تھوڑا اوپر
        stop_loss = trading_range_high + (atr * sl_atr_multiplier)

    # 4. منطقی جانچ اور رسک/ریوارڈ کی تصدیق
    if take_profit is None or stop_loss is None:
        return None

    # یقینی بنائیں کہ TP اور SL انٹری قیمت کے صحیح سمت میں ہیں
    if (signal_type == 'buy' and (take_profit <= last_close or stop_loss >= last_close)) or \
       (signal_type == 'sell' and (take_profit >= last_close or stop_loss <= last_close)):
        logger.warning(f"[{signal_type}] سگنل کے لیے غیر منطقی TP/SL کی سطحیں۔ TP: {take_profit}, SL: {stop_loss}, قیمت: {last_close}")
        return None

    try:
        reward = abs(take_profit - last_close)
        risk = abs(last_close - stop_loss)
        if risk == 0: return None
        
        rr_ratio = reward / risk
        if rr_ratio < min_rr_ratio:
            logger.warning(f"ذہین رینج کا رسک/ریوارڈ تناسب ({rr_ratio:.2f}) کم از کم ({min_rr_ratio}) سے کم ہے۔ سگنل مسترد۔")
            return None
            
    except ZeroDivisionError:
        return None
        
    logger.info(f"ذہین رینج کی بنیاد پر TP/SL ملا: TP={take_profit:.5f}, SL={stop_loss:.5f} (RR: {rr_ratio:.2f})")
    return take_profit, stop_loss
    
