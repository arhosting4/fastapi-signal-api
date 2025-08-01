# filename: patternai.py

import pandas as pd
from typing import Dict

# ★★★ اپ ڈیٹ شدہ فنکشن دستخط ★★★
def detect_patterns(df: pd.DataFrame) -> Dict[str, str]:
    """
    کینڈل اسٹک پیٹرنز کی شناخت کرتا ہے۔
    اب یہ براہ راست پانڈاز ڈیٹا فریم قبول کرتا ہے۔
    """
    if df.empty or len(df) < 2:
        return {"pattern": "ناکافی ڈیٹا", "type": "neutral"}

    # اب ڈیٹا فریم بنانے کی ضرورت نہیں
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # --- پیٹرن کی منطق میں کوئی تبدیلی نہیں ---

    is_bullish_engulfing = (prev['close'] < prev['open'] and last['close'] > last['open'] and last['close'] >= prev['open'] and last['open'] <= prev['close'])
    if is_bullish_engulfing:
        return {"pattern": "Bullish Engulfing", "type": "bullish"}

    is_bearish_engulfing = (prev['close'] > prev['open'] and last['close'] < last['open'] and last['close'] <= prev['open'] and last['open'] >= prev['close'])
    if is_bearish_engulfing:
        return {"pattern": "Bearish Engulfing", "type": "bearish"}

    body_size = abs(last['close'] - last['open'])
    
    # صفر سے تقسیم کی خرابی سے بچنے کے لیے چیک
    if (last['high'] - last['low']) == 0:
        return {"pattern": "کوئی خاص پیٹرن نہیں", "type": "neutral"}

    if body_size < (last['high'] - last['low']) * 0.05:
        return {"pattern": "Doji/Indecision", "type": "neutral"}

    if last['close'] > last['open']:
        upper_wick = last['high'] - last['close']
        lower_wick = last['open'] - last['low']
    else:
        upper_wick = last['high'] - last['open']
        lower_wick = last['close'] - last['low']

    is_hammer = (lower_wick >= body_size * 2) and (upper_wick < body_size)
    if is_hammer:
        return {"pattern": "Hammer", "type": "bullish"}

    is_shooting_star = (upper_wick >= body_size * 2) and (lower_wick < body_size)
    if is_shooting_star:
        return {"pattern": "Shooting Star", "type": "bearish"}

    return {"pattern": "کوئی خاص پیٹرن نہیں", "type": "neutral"}
