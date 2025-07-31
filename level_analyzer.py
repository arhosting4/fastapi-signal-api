# filename: level_analyzer.py

import logging
import pandas as pd
from typing import List, Dict, Optional, Tuple
from config import STRATEGY

logger = logging.getLogger(__name__)

MIN_RISK_REWARD_RATIO = STRATEGY.get("MIN_RISK_REWARD_RATIO", 1.5)
MIN_CONFLUENCE_SCORE = STRATEGY.get("MIN_CONFLUENCE_SCORE", 4)
LEVEL_SCORING_WEIGHTS = STRATEGY.get("LEVEL_SCORING_WEIGHTS", {
    "pivots": 3, "swings": 2, "fibonacci": 2, "psychological": 1
})

# ... (اس فائل کے دیگر فنکشنز جیسے _calculate_pivot_points وغیرہ میں کوئی تبدیلی نہیں) ...
def _calculate_pivot_points(df: pd.DataFrame) -> Dict[str, float]:
    last_day = df.iloc[-1]
    high, low, close = last_day['high'], last_day['low'], last_day['close']
    pivot = (high + low + close) / 3
    return {
        'p': pivot,
        'r1': (2 * pivot) - low, 's1': (2 * pivot) - high,
        'r2': pivot + (high - low), 's2': pivot - (high - low),
    }

def _find_swing_levels(df: pd.DataFrame, window: int = 10) -> Dict[str, List[float]]:
    highs = df['high'].rolling(window=window, center=True).max().dropna().unique()
    lows = df['low'].rolling(window=window, center=True).min().dropna().unique()
    return {"highs": sorted(highs, reverse=True)[:3], "lows": sorted(lows)[:3]}

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
    # ★★★ تبدیلی: اب یہ فنکشن پہلے سے ہی df لیتا ہے، جو کہ درست ہے۔ ★★★
    # صرف اس بات کو یقینی بنانا ہے کہ یہ df کو دوبارہ نہ بنائے
    if len(df) < window * 2:
        return {"trend": "غیر متعین", "zone": "غیر جانبدار", "reason": "ناکافی ڈیٹا۔"}
    
    # df = pd.DataFrame(candles) # یہ لائن یہاں نہیں ہونی چاہیے
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['swing_high'] = df['high'][(df['high'].shift(1) < df['high']) & (df['high'].shift(-1) < df['high'])]
    df['swing_low'] = df['low'][(df['low'].shift(1) > df['low']) & (df['low'].shift(-1) > df['low'])]
    recent_swings = df.tail(window * 2)
    recent_highs = recent_swings['swing_high'].dropna()
    recent_lows = recent_swings['swing_low'].dropna()
    if recent_highs.empty or recent_lows.empty:
        return {"trend": "رینجنگ", "zone": "غیر جانبدار", "reason": "کوئی واضح سوئنگ پوائنٹس نہیں"}
    trend = "رینجنگ"
    if len(recent_highs) >= 2 and len(recent_lows) >= 2:
        if recent_highs.iloc[-1] > recent_highs.iloc[-2] and recent_lows.iloc[-1] > recent_lows.iloc[-2]:
            trend = "اوپر کا رجحان"
        elif recent_highs.iloc[-1] < recent_highs.iloc[-2] and recent_lows.iloc[-1] < recent_lows.iloc[-2]:
            trend = "نیچے کا رجحان"
    return {"trend": trend, "zone": "N/A", "reason": f"موجودہ رجحان {trend} ہے۔"}


# ★★★ یہاں تبدیلی کی گئی ہے ★★★
def find_optimal_tp_sl(df: pd.DataFrame, signal_type: str) -> Optional[Tuple[float, float]]:
    """
    یہ فنکشن اب کینڈلز کی لسٹ کے بجائے براہ راست پانڈاز ڈیٹا فریم لیتا ہے۔
    """
    if len(df) < 34: return None
    
    # df = pd.DataFrame(candles) # ★★★ اس غیر ضروری لائن کو ہٹا دیا گیا ہے ★★★
    
    last_close = df['close'].iloc[-1]
    pivots = list(_calculate_pivot_points(df).values())
    swings = _find_swing_levels(df)
    fib_levels = list(_get_fibonacci_levels(df).values())
    psy_levels = list(_get_psychological_levels(last_close).values())
    all_levels = set(pivots + swings['highs'] + swings['lows'] + fib_levels + psy_levels)
    
    potential_tp_levels = {}
    potential_sl_levels = {}
    for level in all_levels:
        score = 0
        if any(abs(level - p) < (last_close * 0.0005) for p in pivots): score += LEVEL_SCORING_WEIGHTS.get('pivots', 3)
        if any(abs(level - s) < (last_close * 0.0005) for s in swings['highs'] + swings['lows']): score += LEVEL_SCORING_WEIGHTS.get('swings', 2)
        if any(abs(level - f) < (last_close * 0.0005) for f in fib_levels): score += LEVEL_SCORING_WEIGHTS.get('fibonacci', 2)
        if any(abs(level - p) < (last_close * 0.0005) for p in psy_levels): score += LEVEL_SCORING_WEIGHTS.get('psychological', 1)
        
        if score >= MIN_CONFLUENCE_SCORE:
            if level > last_close:
                if signal_type == 'buy': potential_tp_levels[level] = score
                else: potential_sl_levels[level] = score
            else:
                if signal_type == 'sell': potential_tp_levels[level] = score
                else: potential_sl_levels[level] = score

    if not potential_tp_levels or not potential_sl_levels:
        logger.warning(f"[{signal_type}] سگنل کے لیے کافی TP/SL لیولز نہیں ملے۔")
        return None
        
    final_tp = max(potential_tp_levels, key=potential_tp_levels.get) if potential_tp_levels else None
    # SL کی منطق کو درست کیا گیا
    if signal_type == 'buy':
        final_sl = min(potential_sl_levels, key=potential_sl_levels.get) if potential_sl_levels else None
    else: # 'sell'
        final_sl = max(potential_sl_levels, key=potential_sl_levels.get) if potential_sl_levels else None

    if not final_tp or not final_sl:
        return None
        
    try:
        reward = abs(final_tp - last_close)
        risk = abs(last_close - final_sl)
        if risk == 0: return None
        rr_ratio = reward / risk
        if rr_ratio < MIN_RISK_REWARD_RATIO:
            logger.warning(f"بہترین لیولز کا رسک/ریوارڈ تناسب ({rr_ratio:.2f}) بہت کم ہے۔ سگنل مسترد۔")
            return None
    except ZeroDivisionError:
        return None
        
    logger.info(f"کنفلونس کی بنیاد پر TP/SL ملا: TP={final_tp:.5f} (اسکور: {potential_tp_levels.get(final_tp, 0)}), SL={final_sl:.5f} (اسکور: {potential_sl_levels.get(final_sl, 0)})")
    return final_tp, final_sl
    
