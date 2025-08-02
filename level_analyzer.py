# filename: level_analyzer.py

import logging
from typing import List, Dict, Optional, Tuple, NamedTuple
import pandas as pd
import numpy as np

from config import strategy_settings

logger = logging.getLogger(__name__)

# --- کنفیگریشن اور مستقل اقدار ---
MIN_RISK_REWARD_RATIO = strategy_settings.MIN_RISK_REWARD_RATIO
# کنفلونس زون کی کم سے کم طاقت
MIN_CONFLUENCE_STRENGTH = 5 

class Level(NamedTuple):
    """ایک انفرادی تکنیکی لیول کی نمائندگی کرتا ہے۔"""
    price: float
    type: str
    weight: int

# --- لیول کیلکولیشن کے نجی فنکشنز ---

def _calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
    """Average True Range (ATR) کا حساب لگاتا ہے۔"""
    df_copy = df.copy()
    df_copy['h-l'] = df_copy['high'] - df_copy['low']
    df_copy['h-pc'] = abs(df_copy['high'] - df_copy['close'].shift(1))
    df_copy['l-pc'] = abs(df_copy['low'] - df_copy['close'].shift(1))
    tr = df_copy[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean().iloc[-1]
    return atr if pd.notna(atr) and atr > 0 else df['close'].iloc[-1] * 0.001

def _get_pivot_points(df: pd.DataFrame) -> List[Level]:
    """کلاسک پیوٹ پوائنٹس کو لیولز کے طور پر واپس کرتا ہے۔"""
    if len(df) < 2: return []
    last = df.iloc[-2]
    h, l, c = last['high'], last['low'], last['close']
    pivot = (h + l + c) / 3
    return [
        Level(price=(2 * pivot) - l, type='pivot_r', weight=3),
        Level(price=(2 * pivot) - h, type='pivot_s', weight=3),
        Level(price=pivot + (h - l), type='pivot_r', weight=2),
        Level(price=pivot - (h - l), type='pivot_s', weight=2),
    ]

def _get_swing_levels(df: pd.DataFrame, window: int = 10) -> List[Level]:
    """حالیہ سوئنگ ہائی اور لو کو لیولز کے طور پر واپس کرتا ہے۔"""
    if len(df) < window: return []
    highs = df['high'].rolling(window=window, center=True).max().dropna().unique()
    lows = df['low'].rolling(window=window, center=True).min().dropna().unique()
    levels = []
    for high in sorted(list(highs), reverse=True)[:3]:
        levels.append(Level(price=high, type='swing_r', weight=2))
    for low in sorted(list(lows))[:3]:
        levels.append(Level(price=low, type='swing_s', weight=2))
    return levels

def _get_fibonacci_levels(df: pd.DataFrame) -> List[Level]:
    """فبوناچی ریٹریسمنٹ لیولز واپس کرتا ہے۔"""
    if len(df) < 34: return []
    recent_high = df['high'].tail(34).max()
    recent_low = df['low'].tail(34).min()
    price_range = recent_high - recent_low
    if price_range == 0: return []
    return [
        Level(price=recent_high - (price_range * 0.382), type='fib', weight=1),
        Level(price=recent_high - (price_range * 0.500), type='fib', weight=2),
        Level(price=recent_high - (price_range * 0.618), type='fib', weight=1),
    ]

# --- مرکزی فنکشن ---

def find_optimal_tp_sl(df: pd.DataFrame, signal_type: str) -> Optional[Tuple[float, float]]:
    """
    ایک ذہین کلسٹرنگ الگورتھم کا استعمال کرتے ہوئے بہترین TP/SL کا تعین کرتا ہے۔
    """
    if len(df) < 34: return None
    
    last_close = df['close'].iloc[-1]
    atr = _calculate_atr(df)
    
    # 1. تمام ذرائع سے لیولز کو شفاف طریقے سے اکٹھا کریں
    all_levels: List[Level] = []
    all_levels.extend(_get_pivot_points(df))
    all_levels.extend(_get_swing_levels(df))
    all_levels.extend(_get_fibonacci_levels(df))
    
    if not all_levels:
        logger.warning("تجزیے کے لیے کوئی تکنیکی لیولز نہیں ملے۔")
        return None

    # 2. لیولز کو قیمت کے لحاظ سے ترتیب دیں
    all_levels.sort(key=lambda x: x.price)
    
    # 3. متحرک کلسٹرنگ الگورتھم
    # لیولز کے گروپس (کلسٹرز) بنائیں جو ATR کی بنیاد پر ایک دوسرے کے قریب ہوں
    clusters: List[List[Level]] = []
    if all_levels:
        current_cluster = [all_levels[0]]
        # کلسٹر بنانے کے لیے ATR کا 1/4 حصہ فاصلے کے طور پر استعمال کریں
        cluster_distance = atr * 0.25
        
        for i in range(1, len(all_levels)):
            if all_levels[i].price - current_cluster[-1].price <= cluster_distance:
                current_cluster.append(all_levels[i])
            else:
                clusters.append(current_cluster)
                current_cluster = [all_levels[i]]
        clusters.append(current_cluster)

    if not clusters:
        logger.warning("کوئی کنفلونس زون نہیں ملا۔")
        return None

    # 4. ہر کلسٹر کی طاقت کا حساب لگائیں
    strong_zones = []
    for cluster in clusters:
        # طاقت = (مختلف اقسام کی تعداد) * (تمام لیولز کا کل وزن)
        num_types = len(set(level.type for level in cluster))
        total_weight = sum(level.weight for level in cluster)
        strength = num_types * total_weight
        
        # کلسٹر کی اوسط قیمت
        avg_price = np.mean([level.price for level in cluster])
        
        if strength >= MIN_CONFLUENCE_STRENGTH:
            strong_zones.append({'price': avg_price, 'strength': strength})

    # 5. سگنل کی قسم کی بنیاد پر بہترین TP اور SL زونز کا انتخاب کریں
    support_zones = [z for z in strong_zones if z['price'] < last_close]
    resistance_zones = [z for z in strong_zones if z['price'] > last_close]

    if not support_zones or not resistance_zones:
        logger.warning(f"کافی سپورٹ ({len(support_zones)}) یا رزسٹنس ({len(resistance_zones)}) زونز نہیں ملے۔")
        return None

    # سب سے طاقتور زون کو منتخب کریں
    best_support = max(support_zones, key=lambda x: x['strength'])
    best_resistance = max(resistance_zones, key=lambda x: x['strength'])

    final_tp, final_sl = (0.0, 0.0)
    if signal_type == 'buy':
        final_tp = best_resistance['price']
        final_sl = best_support['price']
    else: # sell
        final_tp = best_support['price']
        final_sl = best_resistance['price']

    # 6. رسک/ریوارڈ اور منطقی حیثیت کی حتمی جانچ
    try:
        reward = abs(final_tp - last_close)
        risk = abs(last_close - final_sl)
        if risk == 0 or reward == 0: return None
        
        rr_ratio = reward / risk
        if rr_ratio < MIN_RISK_REWARD_RATIO:
            logger.warning(f"بہترین زون کا رسک/ریوارڈ تناسب ({rr_ratio:.2f}) بہت کم ہے۔")
            return None
            
    except ZeroDivisionError:
        return None
        
    logger.info(f"ذہین کنفلونس کی بنیاد پر TP/SL ملا: TP={final_tp:.5f}, SL={final_sl:.5f} (RR: {rr_ratio:.2f})")
    return final_tp, final_sl

# (find_market_structure فنکشن کو یہاں بغیر تبدیلی کے شامل کیا جا سکتا ہے اگر ضرورت ہو)
