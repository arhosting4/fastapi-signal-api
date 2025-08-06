# filename: level_analyzer.py

import logging
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np

# مقامی امپورٹس
from config import strategy_settings

logger = logging.getLogger(__name__)

# --- مستقل اقدار ---
# اب ہم کم از کم رسک/ریوارڈ یہاں سے نہیں لیں گے، بلکہ یہ متحرک طور پر آئے گا۔
# MIN_CONFLUENCE_SCORE کو بھی متحرک طور پر پاس کیا جائے گا۔
LEVEL_SCORING_WEIGHTS = {
    "pivots": 3, "swings": 2, "fibonacci": 2, "psychological": 1, "atr": 4
}
ATR_PERIOD_FOR_LEVELS = 10

# --- نجی ہیلپر فنکشنز ---

def _calculate_pivot_points(df: pd.DataFrame) -> Dict[str, float]:
    last_candle = df.iloc[-2]
    high, low, close = last_candle['high'], last_candle['low'], last_candle['close']
    pivot = (high + low + close) / 3
    return {
        'p': pivot, 'r1': (2 * pivot) - low, 's1': (2 * pivot) - high,
        'r2': pivot + (high - low), 's2': pivot - (high - low),
    }

def _find_swing_levels(df: pd.DataFrame, window: int = 10) -> Dict[str, List[float]]:
    highs = df['high'].rolling(window=window, center=True).max().dropna().unique()
    lows = df['low'].rolling(window=window, center=True).min().dropna().unique()
    return {"highs": sorted(list(highs), reverse=True)[:3], "lows": sorted(list(lows))[:3]}

def _get_fibonacci_levels(df: pd.DataFrame) -> Dict[str, float]:
    recent_high = df['high'].tail(34).max()
    recent_low = df['low'].tail(34).min()
    price_range = recent_high - recent_low
    if price_range == 0: return {}
    return {
        'fib_23_6': recent_high - (price_range * 0.236),
        'fib_38_2': recent_high - (price_range * 0.382),
        'fib_50_0': recent_high - (price_range * 0.5),
        'fib_61_8': recent_high - (price_range * 0.618),
    }

def _get_psychological_levels(price: float) -> Dict[str, float]:
    if price > 1000: unit = 50.0
    elif price > 10: unit = 0.50
    else: unit = 0.0050
    base = round(price / unit) * unit
    return {'upper_psy': base + unit, 'lower_psy': base - unit}

def _get_atr_levels(df: pd.DataFrame) -> Dict[str, float]:
    high, low, close = df['high'], df['low'], df['close']
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD_FOR_LEVELS, adjust=False).mean().iloc[-1]
    last_close = close.iloc[-1]
    return {'upper_atr': last_close + atr, 'lower_atr': last_close - atr}

# --- عوامی فنکشنز ---

def find_market_structure(df: pd.DataFrame) -> Dict[str, str]:
    if len(df) < 20:
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

def find_optimal_tp_sl(df: pd.DataFrame, signal_type: str, dynamic_params: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """
    متحرک پیرامیٹرز (rr_ratio, confluence_score) کی بنیاد پر بہترین TP/SL کا تعین کرتا ہے۔
    """
    if len(df) < 34: return None
    
    # متحرک پیرامیٹرز حاصل کریں
    min_rr_ratio = dynamic_params.get("rr_ratio", 1.5)
    min_confluence_score = dynamic_params.get("confluence_score", 5)

    last_close = df['close'].iloc[-1]
    
    pivots = list(_calculate_pivot_points(df).values())
    swings = _find_swing_levels(df)
    fib_levels = list(_get_fibonacci_levels(df).values())
    psy_levels = list(_get_psychological_levels(last_close).values())
    atr_levels = list(_get_atr_levels(df).values())
    
    all_levels = set(pivots + swings['highs'] + swings['lows'] + fib_levels + psy_levels + atr_levels)
    
    potential_tp_zones: Dict[float, int] = {}
    potential_sl_zones: Dict[float, int] = {}
    
    proximity = last_close * 0.0005

    for level in all_levels:
        score = 0
        if any(abs(level - p) < proximity for p in pivots): score += LEVEL_SCORING_WEIGHTS['pivots']
        if any(abs(level - s) < proximity for s in swings['highs'] + swings['lows']): score += LEVEL_SCORING_WEIGHTS['swings']
        if any(abs(level - f) < proximity for f in fib_levels): score += LEVEL_SCORING_WEIGHTS['fibonacci']
        if any(abs(level - p) < proximity for p in psy_levels): score += LEVEL_SCORING_WEIGHTS['psychological']
        if any(abs(level - a) < proximity for a in atr_levels): score += LEVEL_SCORING_WEIGHTS['atr']
        
        if score >= min_confluence_score:
            if level > last_close:
                if signal_type == 'buy': potential_tp_zones[level] = score
                else: potential_sl_zones[level] = score
            elif level < last_close:
                if signal_type == 'sell': potential_tp_zones[level] = score
                else: potential_sl_zones[level] = score

    if not potential_tp_zones or not potential_sl_zones:
        logger.warning(f"کافی سپورٹ ({len(potential_sl_zones)}) یا رزسٹنس ({len(potential_tp_zones)}) زونز نہیں ملے۔")
        return None

    best_tp = max(potential_tp_zones, key=potential_tp_zones.get) if signal_type == 'buy' else min(potential_tp_zones, key=potential_tp_zones.get)
    best_sl = min(potential_sl_zones, key=potential_sl_zones.get) if signal_type == 'buy' else max(potential_sl_zones, key=potential_sl_zones.get)

    try:
        reward = abs(best_tp - last_close)
        risk = abs(last_close - best_sl)
        if risk == 0: return None
        
        rr_ratio = reward / risk
        if rr_ratio < min_rr_ratio:
            logger.warning(f"بہترین زون کا رسک/ریوارڈ تناسب ({rr_ratio:.2f})، جو کہ کم از کم ({min_rr_ratio}) سے کم ہے، مسترد۔")
            return None
            
    except ZeroDivisionError:
        return None
        
    logger.info(f"کنفلونس کی بنیاد پر TP/SL ملا: TP={best_tp:.5f}, SL={best_sl:.5f} (RR: {rr_ratio:.2f})")
    return best_tp, best_sl
    
