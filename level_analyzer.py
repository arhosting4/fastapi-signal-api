# filename: level_analyzer.py
# (A powerful, dedicated level analysis module - Final Version 2.0)

import logging
import pandas as pd
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ==============================================================================
# ★★★ لیول اینالائزر ماڈیول (حتمی ورژن) ★★★
# مقصد: کنفلونس کی بنیاد پر بہترین TP/SL لیولز کی شناخت کرنا
# ==============================================================================

def _calculate_pivot_points(df: pd.DataFrame) -> Dict[str, float]:
    """یومیہ کینڈل کی بنیاد پر معیاری پیوٹ پوائنٹس کا حساب لگاتا ہے۔"""
    last_day = df.iloc[-1]
    high, low, close = last_day['high'], last_day['low'], last_day['close']
    pivot = (high + low + close) / 3
    return {
        'p': pivot,
        'r1': (2 * pivot) - low, 's1': (2 * pivot) - high,
        'r2': pivot + (high - low), 's2': pivot - (high - low),
    }

def _find_swing_levels(df: pd.DataFrame, window: int = 10) -> Dict[str, List[float]]:
    """حالیہ سوئنگ اونچائیوں اور نیچائیوں کی شناخت کرتا ہے۔"""
    highs = df['high'].rolling(window=window, center=True).max().dropna().unique()
    lows = df['low'].rolling(window=window, center=True).min().dropna().unique()
    return {"highs": sorted(highs, reverse=True)[:3], "lows": sorted(lows)[:3]}

def _get_fibonacci_levels(df: pd.DataFrame) -> Dict[str, float]:
    """حالیہ حرکت کی بنیاد پر اہم فبوناکی ریٹریسمنٹ لیولز کی شناخت کرتا ہے۔"""
    recent_high = df['high'].tail(34).max()
    recent_low = df['low'].tail(34).min()
    price_range = recent_high - recent_low
    return {
        'fib_23_6': recent_high - (price_range * 0.236),
        'fib_38_2': recent_high - (price_range * 0.382),
        'fib_50_0': recent_high - (price_range * 0.5),
        'fib_61_8': recent_high - (price_range * 0.618),
    }

def _get_psychological_levels(price: float) -> Dict[str, float]:
    """موجودہ قیمت کے قریب ترین نفسیاتی (گول نمبر) لیولز کی شناخت کرتا ہے۔"""
    # قیمت کے مطابق راؤنڈنگ کی اکائی کا تعین کریں (e.g., 1.2345 -> 0.0050)
    if price > 1000: # جیسے XAU/USD
        unit = 50.0
    elif price > 10: # جیسے USD/JPY
        unit = 0.5
    else: # جیسے EUR/USD
        unit = 0.0050
    
    base = round(price / unit) * unit
    return {'upper_psy': base + unit, 'lower_psy': base - unit}

# ==============================================================================
# ★★★ مرکزی فنکشن: بہترین TP/SL تلاش کرنا (اسکورنگ سسٹم کے ساتھ) ★★★
# ==============================================================================

def find_optimal_tp_sl(candles: List[Dict], signal_type: str) -> Optional[Tuple[float, float]]:
    """
    کنفلونس اسکورنگ کی بنیاد پر بہترین TP اور SL لیولز کی شناخت کرتا ہے۔
    """
    if len(candles) < 34: return None
        
    df = pd.DataFrame(candles)
    last_close = df['close'].iloc[-1]
    
    # 1. تمام ممکنہ لیولز کے ذرائع حاصل کریں
    pivots = list(_calculate_pivot_points(df).values())
    swings = _find_swing_levels(df)
    fib_levels = list(_get_fibonacci_levels(df).values())
    psy_levels = list(_get_psychological_levels(last_close).values())

    # 2. تمام ممکنہ لیولز کو ایک جگہ جمع کریں
    all_levels = set(pivots + swings['highs'] + swings['lows'] + fib_levels + psy_levels)
    
    potential_tp_levels = {}
    potential_sl_levels = {}

    # 3. ہر لیول کے لیے کنفلونس اسکور کا حساب لگائیں
    for level in all_levels:
        score = 0
        # ہر ذریعہ جو اس لیول کی تصدیق کرتا ہے، اسکور میں اضافہ کرتا ہے
        if any(abs(level - p) < (last_close * 0.0005) for p in pivots): score += 3
        if any(abs(level - s) < (last_close * 0.0005) for s in swings['highs'] + swings['lows']): score += 2
        if any(abs(level - f) < (last_close * 0.0005) for f in fib_levels): score += 2
        if any(abs(level - p) < (last_close * 0.0005) for p in psy_levels): score += 1
        
        if score > 0:
            if level > last_close:
                if signal_type == 'buy': potential_tp_levels[level] = score
                else: potential_sl_levels[level] = score
            else:
                if signal_type == 'sell': potential_tp_levels[level] = score
                else: potential_sl_levels[level] = score

    if not potential_tp_levels or not potential_sl_levels:
        logger.warning(f"[{signal_type}] سگنل کے لیے کافی TP/SL لیولز نہیں ملے۔")
        return None

    # 4. سب سے زیادہ اسکور والے لیول کا انتخاب کریں
    final_tp = max(potential_tp_levels, key=potential_tp_levels.get)
    final_sl = max(potential_sl_levels, key=potential_sl_levels.get)

    # 5. رسک ٹو ریوارڈ کو یقینی بنائیں
    try:
        reward = abs(final_tp - last_close)
        risk = abs(last_close - final_sl)
        if risk == 0 or (reward / risk) < 1.5:
            logger.warning(f"بہترین لیولز کا رسک/ریوارڈ تناسب ({reward/risk:.2f}) بہت کم ہے۔ سگنل مسترد۔")
            return None
    except ZeroDivisionError:
        return None

    logger.info(f"کنفلونس کی بنیاد پر TP/SL ملا: TP={final_tp:.5f} (اسکور: {potential_tp_levels[final_tp]}), SL={final_sl:.5f} (اسکور: {potential_sl_levels[final_sl]})")
    return final_tp, final_sl
    
