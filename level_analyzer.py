# filename: level_analyzer.py

import logging
from typing import List, Dict, Optional, Tuple

import pandas as pd
import numpy as np

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
ATR_PERIOD_FOR_SL = 14  # ATR کی مدت جو SL بفر کے لیے استعمال ہوگی
ATR_BUFFER_MULTIPLIER = 0.25  # ATR کا کتنا حصہ بفر کے طور پر استعمال کرنا ہے (25%)

# --- نجی ہیلپر فنکشنز ---

def _calculate_atr(df: pd.DataFrame, period: int) -> float:
    """Average True Range (ATR) کا حساب لگاتا ہے۔"""
    if len(df) < period:
        return 0.0
    
    df_copy = df.copy()
    high, low, close = df_copy['high'], df_copy['low'], df_copy['close']
    
    df_copy['h-l'] = high - low
    df_copy['h-pc'] = abs(high - close.shift(1))
    df_copy['l-pc'] = abs(low - close.shift(1))
    
    tr = df_copy[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()
    
    return atr.iloc[-1] if not atr.empty else 0.0

def _calculate_pivot_points(df: pd.DataFrame) -> Dict[str, float]:
    """کلاسک پیوٹ پوائنٹس کا حساب لگاتا ہے۔"""
    last_candle = df.iloc[-2]
    high, low, close = last_candle['high'], last_candle['low'], last_candle['close']
    pivot = (high + low + close) / 3
    return {
        'p': pivot,
        'r1': (2 * pivot) - low, 's1': (2 * pivot) - high,
        'r2': pivot + (high - low), 's2': pivot - (high - low),
    }

def _find_swing_levels(df: pd.DataFrame, window: int = 10) -> Dict[str, List[float]]:
    """حالیہ سوئنگ ہائی اور لو لیولز کی شناخت کرتا ہے۔"""
    highs = df['high'].rolling(window=window, center=True).max().dropna().unique()
    lows = df['low'].rolling(window=window, center=True).min().dropna().unique()
    return {"highs": sorted(list(highs), reverse=True)[:3], "lows": sorted(list(lows))[:3]}

def _get_fibonacci_levels(df: pd.DataFrame) -> Dict[str, float]:
    """فبوناچی ریٹریسمنٹ لیولز کا حساب لگاتا ہے۔"""
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
    """موجودہ قیمت کے قریب نفسیاتی لیولز کی شناخت کرتا ہے۔"""
    if price > 1000: unit = 50.0
    elif price > 10: unit = 0.50
    else: unit = 0.0050
    base = round(price / unit) * unit
    return {'upper_psy': base + unit, 'lower_psy': base - unit}

def _cluster_levels(levels: List[float], proximity_percent: float, price: float) -> List[Tuple[float, int]]:
    """قریبی لیولز کو کلسٹرز میں گروپ کرتا ہے اور ہر کلسٹر کا وزن شدہ اسکور دیتا ہے۔"""
    if not levels:
        return []
    
    proximity = price * proximity_percent
    levels.sort()
    
    clusters = []
    current_cluster = [levels[0]]
    
    for i in range(1, len(levels)):
        if abs(levels[i] - current_cluster[-1]) <= proximity:
            current_cluster.append(levels[i])
        else:
            clusters.append(current_cluster)
            current_cluster = [levels[i]]
    clusters.append(current_cluster)
    
    # ہر کلسٹر کا نمائندہ لیول (اوسط) اور اس کا اسکور (لیولز کی تعداد) واپس کریں
    return [(np.mean(c), len(c)) for c in clusters]

# --- عوامی فنکشنز ---

def find_market_structure(df: pd.DataFrame, window: int = 20) -> Dict[str, str]:
    """مارکیٹ کے حالیہ رجحان کا تعین کرتا ہے۔"""
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

def find_optimal_tp_sl(df: pd.DataFrame, signal_type: str) -> Optional[Tuple[float, float]]:
    """
    مختلف تکنیکی لیولز کو ملا کر اور ان کا کنفلونس اسکور نکال کر بہترین TP/SL کا تعین کرتا ہے۔
    یہ اب SL میں مارکیٹ کے شور سے بچنے کے لیے ATR بفر بھی شامل کرتا ہے۔
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
        logger.warning(f"کافی مضبوط سپورٹ ({len(potential_sl_levels)}) یا رزسٹنس ({len(potential_tp_levels)}) زونز نہیں ملے۔")
        return None

    # سب سے زیادہ اسکور والے لیول کو منتخب کریں
    final_tp = max(potential_tp_levels, key=potential_tp_levels.get) if signal_type == 'buy' else min(potential_tp_levels, key=potential_tp_levels.get)
    final_sl_raw = min(potential_sl_levels, key=potential_sl_levels.get) if signal_type == 'buy' else max(potential_sl_levels, key=potential_sl_levels.get)

    # --- ATR بفر کی منطق ---
    atr = _calculate_atr(df, ATR_PERIOD_FOR_SL)
    if atr > 0:
        buffer = atr * ATR_BUFFER_MULTIPLIER
        logger.info(f"ATR کی بنیاد پر SL بفر کا حساب لگایا گیا: {buffer:.5f}")
        if signal_type == 'buy':
            final_sl = final_sl_raw - buffer
        else: # 'sell'
            final_sl = final_sl_raw + buffer
    else:
        final_sl = final_sl_raw

    # رسک/ریوارڈ تناسب کو چیک کریں
    try:
        reward = abs(final_tp - last_close)
        risk = abs(last_close - final_sl)
        if risk == 0: return None
        
        rr_ratio = reward / risk
        if rr_ratio < MIN_RISK_REWARD_RATIO:
            logger.warning(f"بہترین زون کا رسک/ریوارڈ تناسب ({rr_ratio:.2f}) بہت کم ہے۔")
            return None
            
    except ZeroDivisionError:
        return None
        
    logger.info(f"حتمی TP/SL ملا: TP={final_tp:.5f}, SL={final_sl:.5f} (RR: {rr_ratio:.2f})")
    return final_tp, final_sl
