# filename: level_analyzer.py

import logging
from typing import List, Dict, Optional, Tuple

import pandas as pd

# مقامی امپورٹس
from config import strategy_settings

logger = logging.getLogger(__name__)

# --- کنفیگریشن سے مستقل اقدار ---
MIN_RISK_REWARD_RATIO = strategy_settings.MIN_RISK_REWARD_RATIO
MIN_CONFLUENCE_SCORE = strategy_settings.MIN_CONFLUENCE_SCORE
LEVEL_SCORING_WEIGHTS = {
    "pivots": 3,
    "swings": 2,
    "fibonacci": 2,
    "psychological": 1
}

# --- نجی ہیلپر فنکشنز برائے لیول کیلکولیشن ---

def _calculate_pivot_points(df: pd.DataFrame) -> Dict[str, float]:
    """کلاسک پیوٹ پوائنٹس (R1, S1, R2, S2) کا حساب لگاتا ہے۔"""
    if len(df) < 2:
        return {}
    last_candle = df.iloc[-2] # حساب کے لیے پچھلی مکمل شدہ کینڈل کا استعمال کریں
    high, low, close = last_candle['high'], last_candle['low'], last_candle['close']
    pivot = (high + low + close) / 3
    return {
        'p': pivot,
        'r1': (2 * pivot) - low, 's1': (2 * pivot) - high,
        'r2': pivot + (high - low), 's2': pivot - (high - low),
    }

def _find_swing_levels(df: pd.DataFrame, window: int = 10) -> Dict[str, List[float]]:
    """حالیہ سوئنگ ہائی اور لو لیولز کی شناخت کرتا ہے۔"""
    if len(df) < window:
        return {"highs": [], "lows": []}
    highs = df['high'].rolling(window=window, center=True).max().dropna().unique()
    lows = df['low'].rolling(window=window, center=True).min().dropna().unique()
    # سب سے اہم (حالیہ) 3 لیولز واپس کریں
    return {"highs": sorted(list(highs), reverse=True)[:3], "lows": sorted(list(lows))[:3]}

def _get_fibonacci_levels(df: pd.DataFrame) -> Dict[str, float]:
    """حالیہ رینج کی بنیاد پر فبوناچی ریٹریسمنٹ لیولز کا حساب لگاتا ہے۔"""
    if len(df) < 34:
        return {}
    recent_high = df['high'].tail(34).max()
    recent_low = df['low'].tail(34).min()
    price_range = recent_high - recent_low
    if price_range == 0: 
        return {}
    return {
        'fib_23_6': recent_high - (price_range * 0.236),
        'fib_38_2': recent_high - (price_range * 0.382),
        'fib_50_0': recent_high - (price_range * 0.5),
        'fib_61_8': recent_high - (price_range * 0.618),
    }

def _get_psychological_levels(price: float) -> Dict[str, float]:
    """موجودہ قیمت کے قریب اہم نفسیاتی (گول نمبر) لیولز کی شناخت کرتا ہے۔"""
    if price > 1000: unit = 50.0
    elif price > 10: unit = 0.50
    else: unit = 0.0050
    base = round(price / unit) * unit
    return {'upper_psy': base + unit, 'lower_psy': base - unit}

# --- عوامی فنکشنز ---

def find_market_structure(df: pd.DataFrame, window: int = 20) -> Dict[str, str]:
    """
    مارکیٹ کے حالیہ رجحان (trend) کا تعین کرتا ہے (اوپر، نیچے، یا رینجنگ)۔
    """
    if len(df) < window:
        return {"trend": "غیر متعین", "reason": "ناکافی ڈیٹا۔"}
    
    # سوئنگ ہائی اور لو کی شناخت کے لیے ایک سادہ طریقہ
    df_copy = df.copy()
    df_copy['swing_high'] = df_copy['high'][(df_copy['high'].shift(1) < df_copy['high']) & (df_copy['high'].shift(-1) < df_copy['high'])]
    df_copy['swing_low'] = df_copy['low'][(df_copy['low'].shift(1) > df_copy['low']) & (df_copy['low'].shift(-1) > df_copy['low'])]
    
    recent_highs = df_copy['swing_high'].dropna().tail(2).values
    recent_lows = df_copy['swing_low'].dropna().tail(2).values

    if len(recent_highs) < 2 or len(recent_lows) < 2:
        return {"trend": "رینجنگ", "reason": "کوئی واضح سوئنگ پوائنٹس نہیں"}
    
    trend = "رینجنگ"
    # ہائر ہائی اور ہائر لو -> اوپر کا رجحان
    if recent_highs[-1] > recent_highs[-2] and recent_lows[-1] > recent_lows[-2]:
        trend = "اوپر کا رجحان"
    # لوئر ہائی اور لوئر لو -> نیچے کا رجحان
    elif recent_highs[-1] < recent_highs[-2] and recent_lows[-1] < recent_lows[-2]:
        trend = "نیچے کا رجحان"
        
    return {"trend": trend, "reason": f"مارکیٹ کی ساخت {trend} کی نشاندہی کرتی ہے۔"}

def find_optimal_tp_sl(df: pd.DataFrame, signal_type: str) -> Optional[Tuple[float, float]]:
    """
    مختلف تکنیکی لیولز کو ملا کر اور ان کا کنفلونس اسکور نکال کر بہترین TP/SL کا تعین کرتا ہے۔
    """
    if len(df) < 34: 
        return None
    
    last_close = df['close'].iloc[-1]
    
    # تمام ممکنہ سپورٹ/رزسٹنس لیولز کو اکٹھا کریں
    pivots = list(_calculate_pivot_points(df).values())
    swings = _find_swing_levels(df)
    fib_levels = list(_get_fibonacci_levels(df).values())
    psy_levels = list(_get_psychological_levels(last_close).values())
    
    all_levels = set(pivots + swings['highs'] + swings['lows'] + fib_levels + psy_levels)
    
    potential_tp_levels: Dict[float, int] = {}
    potential_sl_levels: Dict[float, int] = {}
    
    proximity = last_close * 0.0005 # قیمت کے قریب ہونے کی حد (0.05%)

    # ہر لیول کا کنفلونس اسکور نکالیں
    for level in all_levels:
        score = 0
        if any(abs(level - p) < proximity for p in pivots): score += LEVEL_SCORING_WEIGHTS['pivots']
        if any(abs(level - s) < proximity for s in swings['highs'] + swings['lows']): score += LEVEL_SCORING_WEIGHTS['swings']
        if any(abs(level - f) < proximity for f in fib_levels): score += LEVEL_SCORING_WEIGHTS['fibonacci']
        if any(abs(level - p) < proximity for p in psy_levels): score += LEVEL_SCORING_WEIGHTS['psychological']
        
        if score >= MIN_CONFLUENCE_SCORE:
            if level > last_close:
                if signal_type == 'buy': potential_tp_levels[level] = score
                else: potential_sl_levels[level] = score
            elif level < last_close:
                if signal_type == 'sell': potential_tp_levels[level] = score
                else: potential_sl_levels[level] = score

    if not potential_tp_levels or not potential_sl_levels:
        logger.warning(f"[{signal_type}] سگنل کے لیے کافی مضبوط TP/SL لیولز ({len(potential_tp_levels)} TP, {len(potential_sl_levels)} SL) نہیں ملے۔")
        return None

    # سب سے زیادہ اسکور والے لیول کو منتخب کریں
    final_tp = max(potential_tp_levels, key=potential_tp_levels.get) if signal_type == 'buy' else min(potential_tp_levels, key=potential_tp_levels.get)
    final_sl = min(potential_sl_levels, key=potential_sl_levels.get) if signal_type == 'buy' else max(potential_sl_levels, key=potential_sl_levels.get)

    # رسک/ریوارڈ تناسب کو چیک کریں
    try:
        reward = abs(final_tp - last_close)
        risk = abs(last_close - final_sl)
        if risk == 0: return None # صفر رسک سے بچیں
        
        rr_ratio = reward / risk
        if rr_ratio < MIN_RISK_REWARD_RATIO:
            logger.warning(f"بہترین لیولز کا رسک/ریوارڈ تناسب ({rr_ratio:.2f}) بہت کم ہے۔ سگنل مسترد۔")
            return None
            
    except ZeroDivisionError:
        return None
        
    logger.info(f"کنفلونس کی بنیاد پر TP/SL ملا: TP={final_tp:.5f}, SL={final_sl:.5f} (RR: {rr_ratio:.2f})")
    return final_tp, final_sl
    
