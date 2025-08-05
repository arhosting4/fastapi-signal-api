# filename: level_analyzer.py

import logging
from typing import List, Dict, Optional, Tuple

import pandas as pd
import numpy as np

from config import strategy_settings

logger = logging.getLogger(__name__)

# --- کنفیگریشن سے مستقل اقدار ---
MIN_CONFLUENCE_SCORE = strategy_settings.MIN_CONFLUENCE_SCORE
LEVEL_SCORING_WEIGHTS = {
    "pivots": 3, "swings": 2, "fibonacci": 2, "psychological": 1
}

# ... (نجی ہیلپر فنکشنز میں کوئی تبدیلی نہیں) ...
def _calculate_pivot_points(df: pd.DataFrame) -> Dict[str, float]:
    last_candle = df.iloc[-2]
    high, low, close = last_candle['high'], last_candle['low'], last_candle['close']
    pivot = (high + low + close) / 3
    return {'p': pivot, 'r1': (2 * pivot) - low, 's1': (2 * pivot) - high, 'r2': pivot + (high - low), 's2': pivot - (high - low)}

def _find_swing_levels(df: pd.DataFrame, window: int = 10) -> Dict[str, List[float]]:
    highs = df['high'].rolling(window=window, center=True).max().dropna().unique()
    lows = df['low'].rolling(window=window, center=True).min().dropna().unique()
    return {"highs": sorted(list(highs), reverse=True)[:3], "lows": sorted(list(lows))[:3]}

def _get_fibonacci_levels(df: pd.DataFrame) -> Dict[str, float]:
    recent_high = df['high'].tail(34).max()
    recent_low = df['low'].tail(34).min()
    price_range = recent_high - recent_low
    if price_range == 0: return {}
    return {'fib_23_6': recent_high - (price_range * 0.236), 'fib_38_2': recent_high - (price_range * 0.382), 'fib_50_0': recent_high - (price_range * 0.5), 'fib_61_8': recent_high - (price_range * 0.618)}

def _get_psychological_levels(price: float) -> Dict[str, float]:
    if price > 1000: unit = 50.0
    elif price > 10: unit = 0.50
    else: unit = 0.0050
    base = round(price / unit) * unit
    return {'upper_psy': base + unit, 'lower_psy': base - unit}

def find_market_structure(df: pd.DataFrame, window: int = 20) -> Dict[str, str]:
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

def find_optimal_tp_sl_for_scalping(df: pd.DataFrame, signal_type: str, symbol_personality: Dict) -> Optional[Tuple[float, float]]:
    """اسکیلپنگ کے لیے بہترین TP/SL کا تعین کرتا ہے، جس میں ATR بفر اور شخصیت شامل ہے۔"""
    if len(df) < 34: return None
    
    last_close = df['close'].iloc[-1]
    
    # ATR کا حساب لگائیں
    tr = pd.concat([df['high'] - df['low'], abs(df['high'] - df['close'].shift()), abs(df['low'] - df['close'].shift())], axis=1).max(axis=1)
    atr = tr.ewm(span=14, adjust=False).mean().iloc[-1]
    
    volatility_multiplier = symbol_personality.get("volatility_multiplier", 1.5)
    min_rr_ratio = symbol_personality.get("min_rr_ratio", 1.5)
    
    # کم از کم SL بفر
    min_sl_buffer = atr * volatility_multiplier
    
    # تمام ممکنہ سپورٹ/رزسٹنس لیولز کو اکٹھا کریں
    pivots = list(_calculate_pivot_points(df).values())
    swings = _find_swing_levels(df)
    fib_levels = list(_get_fibonacci_levels(df).values())
    psy_levels = list(_get_psychological_levels(last_close).values())
    all_levels = set(pivots + swings['highs'] + swings['lows'] + fib_levels + psy_levels)
    
    potential_tp_levels: Dict[float, int] = {}
    potential_sl_levels: Dict[float, int] = {}
    
    proximity = last_close * 0.0005

    for level in all_levels:
        score = 0
        if any(abs(level - p) < proximity for p in pivots): score += LEVEL_SCORING_WEIGHTS['pivots']
        if any(abs(level - s) < proximity for s in swings['highs'] + swings['lows']): score += LEVEL_SCORING_WEIGHTS['swings']
        if any(abs(level - f) < proximity for f in fib_levels): score += LEVEL_SCORING_WEIGHTS['fibonacci']
        if any(abs(level - p) < proximity for p in psy_levels): score += LEVEL_SCORING_WEIGHTS['psychological']
        
        if score >= MIN_CONFLUENCE_SCORE:
            if level > last_close:
                if signal_type == 'buy': potential_tp_levels[level] = score
                else:
                    # SL کو کم از کم بفر سے باہر ہونا چاہیے
                    if abs(level - last_close) > min_sl_buffer:
                        potential_sl_levels[level] = score
            elif level < last_close:
                if signal_type == 'sell': potential_tp_levels[level] = score
                else:
                    if abs(level - last_close) > min_sl_buffer:
                        potential_sl_levels[level] = score

    if not potential_tp_levels or not potential_sl_levels:
        logger.warning(f"[{signal_type}] سگنل کے لیے کافی مضبوط یا محفوظ فاصلے پر TP/SL لیولز نہیں ملے۔")
        return None

    final_tp = max(potential_tp_levels, key=potential_tp_levels.get) if signal_type == 'buy' else min(potential_tp_levels, key=potential_tp_levels.get)
    final_sl = min(potential_sl_levels, key=potential_sl_levels.get) if signal_type == 'buy' else max(potential_sl_levels, key=potential_sl_levels.get)

    try:
        reward = abs(final_tp - last_close)
        risk = abs(last_close - final_sl)
        if risk == 0: return None
        
        rr_ratio = reward / risk
        if rr_ratio < min_rr_ratio:
            logger.warning(f"بہترین زون کا رسک/ریوارڈ تناسب ({rr_ratio:.2f})، جو کہ کم از کم ({min_rr_ratio}) سے کم ہے، مسترد۔")
            return None
            
    except ZeroDivisionError:
        return None
        
    logger.info(f"کنفلونس کی بنیاد پر TP/SL ملا: TP={final_tp:.5f}, SL={final_sl:.5f} (RR: {rr_ratio:.2f})")
    return final_tp, final_sl
    
