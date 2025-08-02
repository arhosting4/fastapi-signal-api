# filename: level_analyzer.py

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd

from config import strategy_settings

logger = logging.getLogger(__name__)

# ... (دیگر فنکشنز میں کوئی تبدیلی نہیں) ...
def _calculate_pivot_points(df: pd.DataFrame) -> Dict[str, float]:
    last_candle = df.iloc[-1]
    high, low, close = last_candle['high'], last_candle['low'], last_candle['close']
    pivot = (high + low + close) / 3
    return {
        'p': pivot,
        'r1': (2 * pivot) - low, 's1': (2 * pivot) - high,
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
    elif price > 10: unit = 0.5
    else: unit = 0.0050
    base = round(price / unit) * unit
    return {'upper_psy': base + unit, 'lower_psy': base - unit}

def find_market_structure(df: pd.DataFrame, window: int = 10) -> Dict[str, str]:
    if len(df) < window * 2:
        return {"trend": "غیر متعین", "zone": "غیر جانبدار", "reason": "ناکافی ڈیٹا۔"}
    df_copy = df.copy()
    df_copy['swing_high'] = df_copy['high'][(df_copy['high'].shift(1) < df_copy['high']) & (df_copy['high'].shift(-1) < df_copy['high'])]
    df_copy['swing_low'] = df_copy['low'][(df_copy['low'].shift(1) > df_copy['low']) & (df_copy['low'].shift(-1) > df_copy['low'])]
    recent_swings = df_copy.tail(window * 2)
    recent_highs = recent_swings['swing_high'].dropna()
    recent_lows = recent_swings['swing_low'].dropna()
    if len(recent_highs) < 2 or len(recent_lows) < 2:
        return {"trend": "رینجنگ", "zone": "غیر جانبدار", "reason": "کوئی واضح سوئنگ پوائنٹس نہیں"}
    trend = "رینجنگ"
    if recent_highs.iloc[-1] > recent_highs.iloc[-2] and recent_lows.iloc[-1] > recent_lows.iloc[-2]:
        trend = "اوپر کا رجحان"
    elif recent_highs.iloc[-1] < recent_highs.iloc[-2] and recent_lows.iloc[-1] < recent_lows.iloc[-2]:
        trend = "نیچے کا رجحان"
    return {"trend": trend, "zone": "N/A", "reason": f"موجودہ رجحان {trend} ہے۔"}

def find_optimal_tp_sl(df: pd.DataFrame, signal_type: str) -> Optional[Tuple[float, float]]:
    if len(df) < 34: return None
    
    last_close = df['close'].iloc[-1]
    
    pivots = list(_calculate_pivot_points(df).values())
    swings = _find_swing_levels(df)
    fib_levels = list(_get_fibonacci_levels(df).values())
    psy_levels = list(_get_psychological_levels(last_close).values())
    
    all_levels = set(pivots + swings['highs'] + swings['lows'] + fib_levels + psy_levels)
    
    potential_tp_levels = {}
    potential_sl_levels = {}
    
    proximity = last_close * 0.0005

    for level in all_levels:
        score = 0
        if any(abs(level - p) < proximity for p in pivots): score += strategy_settings.LEVEL_SCORING_WEIGHTS.get('pivots', 3)
        if any(abs(level - s) < proximity for s in swings['highs'] + swings['lows']): score += strategy_settings.LEVEL_SCORING_WEIGHTS.get('swings', 2)
        if any(abs(level - f) < proximity for f in fib_levels): score += strategy_settings.LEVEL_SCORING_WEIGHTS.get('fibonacci', 2)
        if any(abs(level - p) < proximity for p in psy_levels): score += strategy_settings.LEVEL_SCORING_WEIGHTS.get('psychological', 1)
        
        if score >= strategy_settings.MIN_CONFLUENCE_SCORE:
            # ★★★ حل: سخت منطقی چیکس ★★★
            if signal_type == 'buy':
                # TP کے لیے، لیول انٹری سے اوپر ہونا چاہیے
                if level > last_close:
                    potential_tp_levels[level] = score
                # SL کے لیے، لیول انٹری سے نیچے ہونا چاہیے
                elif level < last_close:
                    potential_sl_levels[level] = score
            elif signal_type == 'sell':
                # TP کے لیے، لیول انٹری سے نیچے ہونا چاہیے
                if level < last_close:
                    potential_tp_levels[level] = score
                # SL کے لیے، لیول انٹری سے اوپر ہونا چاہیے
                elif level > last_close:
                    potential_sl_levels[level] = score

    if not potential_tp_levels or not potential_sl_levels:
        logger.warning(f"[{signal_type}] سگنل کے لیے کافی TP/SL لیولز نہیں ملے۔ TP ملے: {len(potential_tp_levels)}, SL ملے: {len(potential_sl_levels)}")
        return None

    # اب ہم یقین کر سکتے ہیں کہ تمام لیولز صحیح سمت میں ہیں
    if signal_type == 'buy':
        final_tp = min(potential_tp_levels.keys()) # سب سے قریبی TP
        final_sl = max(potential_sl_levels.keys()) # سب سے قریبی SL
    else: # signal_type == 'sell'
        final_tp = max(potential_tp_levels.keys()) # سب سے قریبی TP
        final_sl = min(potential_sl_levels.keys()) # سب سے قریبی SL

    try:
        reward = abs(final_tp - last_close)
        risk = abs(last_close - final_sl)
        if risk == 0: return None
        
        rr_ratio = reward / risk
        if rr_ratio < strategy_settings.MIN_RISK_REWARD_RATIO:
            logger.warning(f"بہترین لیولز کا رسک/ریوارڈ تناسب ({rr_ratio:.2f}) بہت کم ہے۔ سگنل مسترد۔")
            return None
            
    except ZeroDivisionError:
        return None
        
    logger.info(f"کنفلونس کی بنیاد پر TP/SL ملا: TP={final_tp:.5f}, SL={final_sl:.5f} (RR: {rr_ratio:.2f})")
    return final_tp, final_sl
    
