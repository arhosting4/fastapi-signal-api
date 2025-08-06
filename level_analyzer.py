import logging
from typing import List, Dict, Optional, Tuple

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def _find_swing_levels(df: pd.DataFrame, window: int = 10) -> Dict[str, List[float]]:
    """
    ڈیٹا فریم میں حالیہ سوئنگ ہائی اور لو لیولز کو تلاش کرتا ہے۔
    """
    # 'center=True' اس بات کو یقینی بناتا ہے کہ ایک پوائنٹ کو سوئنگ سمجھنے کے لیے اس کے دونوں طرف کینڈلز ہوں
    highs = df['high'].rolling(window=window, center=True).max().dropna().unique()
    lows = df['low'].rolling(window=window, center=True).min().dropna().unique()
    
    # تازہ ترین 3 لیولز واپس کریں
    return {"highs": sorted(list(highs), reverse=True)[:3], "lows": sorted(list(lows))[:3]}

def find_market_structure(df: pd.DataFrame, window: int = 20) -> Dict[str, str]:
    """
    مارکیٹ کی ساخت (اوپر/نیچے کا رجحان یا رینجنگ) کا تعین کرتا ہے۔
    """
    if len(df) < window:
        return {"trend": "غیر متعین", "reason": "ناکافی ڈیٹا۔"}
    
    df_copy = df.copy()
    # سوئنگ پوائنٹس کی شناخت کریں
    df_copy['swing_high'] = df_copy['high'][(df_copy['high'].shift(1) < df_copy['high']) & (df_copy['high'].shift(-1) < df_copy['high'])]
    df_copy['swing_low'] = df_copy['low'][(df_copy['low'].shift(1) > df_copy['low']) & (df_copy['low'].shift(-1) > df_copy['low'])]
    
    recent_highs = df_copy['swing_high'].dropna().tail(2).values
    recent_lows = df_copy['swing_low'].dropna().tail(2).values
    
    if len(recent_highs) < 2 or len(recent_lows) < 2:
        return {"trend": "رینجنگ", "reason": "کوئی واضح سوئنگ پوائنٹس نہیں"}
        
    trend = "رینجنگ"
    # ہائر ہائی اور ہائر لو = اوپر کا رجحان
    if recent_highs[-1] > recent_highs[-2] and recent_lows[-1] > recent_lows[-2]:
        trend = "اوپر کا رجحان"
    # لوئر ہائی اور لوئر لو = نیچے کا رجحان
    elif recent_highs[-1] < recent_highs[-2] and recent_lows[-1] < recent_lows[-2]:
        trend = "نیچے کا رجحان"
        
    return {"trend": trend, "reason": f"مارکیٹ کی ساخت {trend} کی نشاندہی کرتی ہے۔"}

def find_optimal_tp_sl_for_scalping(df: pd.DataFrame, signal_type: str, symbol_personality: Dict) -> Optional[Tuple[float, float]]:
    """
    اسکیلپنگ کے لیے بہترین TP/SL کا تعین کرتا ہے، جو سوئنگ لیولز اور ATR پر مبنی ہے۔
    """
    if len(df) < 34: return None
    
    last_close = df['close'].iloc[-1]
    
    # ATR کا حساب لگائیں
    tr = pd.concat([df['high'] - df['low'], abs(df['high'] - df['close'].shift()), abs(df['low'] - df['close'].shift())], axis=1).max(axis=1)
    atr = tr.ewm(span=14, adjust=False).mean().iloc[-1]
    
    # اثاثہ کی شخصیت سے پیرامیٹرز حاصل کریں
    volatility_multiplier = symbol_personality.get("volatility_multiplier", 1.5)
    min_rr_ratio = symbol_personality.get("min_rr_ratio", 1.5)
    
    # اسٹاپ لاس کا تعین ATR کی بنیاد پر کریں
    sl_distance = atr * volatility_multiplier
    
    if signal_type == 'buy':
        stop_loss = last_close - sl_distance
    else: # sell
        stop_loss = last_close + sl_distance

    # ٹیک پرافٹ کا تعین اگلے سوئنگ لیول کی بنیاد پر کریں
    swing_levels = _find_swing_levels(df)
    
    potential_tp = None
    if signal_type == 'buy' and swing_levels['highs']:
        # قریب ترین سوئنگ ہائی تلاش کریں جو موجودہ قیمت سے اوپر ہو
        valid_highs = [h for h in swing_levels['highs'] if h > last_close]
        if valid_highs:
            potential_tp = min(valid_highs)
    elif signal_type == 'sell' and swing_levels['lows']:
        # قریب ترین سوئنگ لو تلاش کریں جو موجودہ قیمت سے نیچے ہو
        valid_lows = [l for l in swing_levels['lows'] if l < last_close]
        if valid_lows:
            potential_tp = max(valid_lows)

    # اگر کوئی مناسب سوئنگ لیول نہیں ملتا تو رسک/ریوارڈ کی بنیاد پر TP سیٹ کریں
    if potential_tp is None:
        potential_tp = last_close + (sl_distance * min_rr_ratio) if signal_type == 'buy' else last_close - (sl_distance * min_rr_ratio)

    # رسک/ریوارڈ تناسب کی تصدیق کریں
    try:
        reward = abs(potential_tp - last_close)
        risk = abs(last_close - stop_loss)
        if risk == 0: return None
        
        rr_ratio = reward / risk
        if rr_ratio < min_rr_ratio:
            logger.warning(f"تجویز کردہ TP/SL کا رسک/ریوارڈ تناسب ({rr_ratio:.2f}) کم از کم ({min_rr_ratio}) سے کم ہے۔")
            # اگر RR کم ہے تو SL کو تھوڑا قریب لائیں تاکہ RR بہتر ہو سکے، لیکن ATR سے کم نہیں
            new_risk = reward / min_rr_ratio
            if signal_type == 'buy':
                stop_loss = max(stop_loss, last_close - new_risk)
            else:
                stop_loss = min(stop_loss, last_close + new_risk)

    except ZeroDivisionError:
        return None
        
    logger.info(f"بہترین TP/SL ملا: TP={potential_tp:.5f}, SL={stop_loss:.5f}")
    return potential_tp, stop_loss
    
