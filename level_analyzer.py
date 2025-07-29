# filename: level_analyzer.py

import logging
import pandas as pd
from typing import List, Dict, Optional, Tuple
from config import STRATEGY

logger = logging.getLogger(__name__)

MIN_RISK_REWARD_RATIO = STRATEGY["MIN_RISK_REWARD_RATIO"]
MIN_CONFLUENCE_SCORE = STRATEGY["MIN_CONFLUENCE_SCORE"]

# ==============================================================================
# ★★★ کنفلونس انجن (Confluence Engine) v3.0 ★★★
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
        'r3': high + 2 * (pivot - low), 's3': low - 2 * (high - pivot)
    }

def _find_swing_levels(df: pd.DataFrame, window: int = 15) -> Dict[str, List[float]]:
    """حالیہ اور اہم سوئنگ اونچائیوں اور نیچائیوں کی شناخت کرتا ہے۔"""
    highs = df['high'].rolling(window=window, center=True).max().dropna().unique()
    lows = df['low'].rolling(window=window, center=True).min().dropna().unique()
    return {"highs": sorted(highs, reverse=True)[:5], "lows": sorted(lows)[:5]}

def _get_fibonacci_levels(df: pd.DataFrame) -> Dict[str, float]:
    """حالیہ 50 کینڈلز کی حرکت کی بنیاد پر اہم فبوناکی لیولز کی شناخت کرتا ہے۔"""
    recent_high = df['high'].tail(50).max()
    recent_low = df['low'].tail(50).min()
    price_range = recent_high - recent_low
    if price_range == 0: return {}
    return {
        'fib_23_6': recent_high - (price_range * 0.236),
        'fib_38_2': recent_high - (price_range * 0.382),
        'fib_50_0': recent_high - (price_range * 0.5),
        'fib_61_8': recent_high - (price_range * 0.618),
    }

def _get_psychological_levels(price: float) -> Dict[str, float]:
    """موجودہ قیمت کے قریب ترین نفسیاتی (گول نمبر) لیولز کی شناخت کرتا ہے۔"""
    if price > 1000: unit = 25.0
    elif price > 10: unit = 0.25
    else: unit = 0.0050
    base = round(price / unit) * unit
    return {'upper_psy': base + unit, 'lower_psy': base - unit}

def find_market_structure(candles: List[Dict], window: int = 15) -> Dict[str, str]:
    """مارکیٹ کی ساخت (اوپر/نیچے کا رجحان) کا تجزیہ کرتا ہے۔"""
    if len(candles) < window * 2:
        return {"trend": "غیر متعین"}

    df = pd.DataFrame(candles)
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    
    recent_highs = df['high'].rolling(window).max()
    recent_lows = df['low'].rolling(window).min()

    if recent_highs.iloc[-1] > recent_highs.iloc[-2] and recent_lows.iloc[-1] > recent_lows.iloc[-2]:
        return {"trend": "اوپر کا رجحان"}
    elif recent_highs.iloc[-1] < recent_lows.iloc[-2] and recent_lows.iloc[-1] < recent_lows.iloc[-2]:
        return {"trend": "نیچے کا رجحان"}
    else:
        return {"trend": "رینجنگ"}

def find_optimal_tp_sl(candles: List[Dict], signal_type: str) -> Optional[Tuple[float, float]]:
    """
    صرف اعلیٰ کنفلونس والے TP اور SL لیولز کی شناخت کرتا ہے۔
    """
    if len(candles) < 50: return None
        
    df = pd.DataFrame(candles)
    last_close = df['close'].iloc[-1]
    
    # --- تمام ممکنہ لیولز کو اکٹھا کریں ---
    pivots = list(_calculate_pivot_points(df).values())
    swings = _find_swing_levels(df)
    fib_levels = list(_get_fibonacci_levels(df).values())
    psy_levels = list(_get_psychological_levels(last_close).values())
    all_levels = set(pivots + swings['highs'] + swings['lows'] + fib_levels + psy_levels)
    
    potential_tp_levels = {}
    potential_sl_levels = {}

    # --- ہر لیول کا کنفلونس اسکور نکالیں ---
    for level in all_levels:
        score = 0
        proximity_threshold = last_close * 0.001 
        if any(abs(level - p) < proximity_threshold for p in pivots): score += 3
        if any(abs(level - s) < proximity_threshold for s in swings['highs'] + swings['lows']): score += 3
        if any(abs(level - f) < proximity_threshold for f in fib_levels): score += 2
        if any(abs(level - p) < proximity_threshold for p in psy_levels): score += 1
        
        if score > 0:
            if level > last_close:
                if signal_type == 'buy': potential_tp_levels[level] = score
                else: potential_sl_levels[level] = score
            else:
                if signal_type == 'sell': potential_tp_levels[level] = score
                else: potential_sl_levels[level] = score

    # --- صرف اعلیٰ اسکور والے لیولز کو فلٹر کریں ---
    strong_tp_levels = {k: v for k, v in potential_tp_levels.items() if v >= MIN_CONFLUENCE_SCORE}
    strong_sl_levels = {k: v for k, v in potential_sl_levels.items() if v >= MIN_CONFLUENCE_SCORE}

    if not strong_tp_levels or not strong_sl_levels:
        logger.warning(f"کوئی اعلیٰ کنفلونس (اسکور >= {MIN_CONFLUENCE_SCORE}) والے TP/SL لیولز نہیں ملے۔")
        return None

    # --- بہترین لیول کا انتخاب ---
    final_tp = min(strong_tp_levels.keys(), key=lambda k: abs(k - last_close))
    final_sl = min(strong_sl_levels.keys(), key=lambda k: abs(k - last_close))

    # --- حتمی رسک/ریوارڈ کی جانچ ---
    try:
        reward = abs(final_tp - last_close)
        risk = abs(last_close - final_sl)
        if risk == 0 or (reward / risk) < MIN_RISK_REWARD_RATIO:
            logger.warning(f"بہترین لیولز کا رسک/ریوارڈ تناسب ({reward/risk:.2f}) کم ہے۔ سگنل مسترد۔")
            return None
    except ZeroDivisionError:
        return None

    logger.info(f"اعلیٰ کنفلونس TP/SL ملا: TP={final_tp:.5f} (اسکور: {strong_tp_levels.get(final_tp, 0)}), SL={final_sl:.5f} (اسکور: {strong_sl_levels.get(final_sl, 0)})")
    return final_tp, final_sl
    
