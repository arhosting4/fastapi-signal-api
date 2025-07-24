# filename: patternai.py
import pandas as pd
from typing import List, Dict

from schemas import Candle

def detect_patterns(candles: List[Candle]) -> Dict[str, str]:
    """
    کینڈل اسٹک پیٹرنز کی شناخت کرتا ہے۔ یہ ایک سادہ اور قابل اعتماد نفاذ ہے۔
    """
    if len(candles) < 2:
        return {"pattern": "ناکافی ڈیٹا", "type": "neutral"}

    df = pd.DataFrame([c.dict() for c in candles])

    # آخری دو کینڈلز حاصل کریں
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # --- پیٹرن کی منطق ---

    # Bullish Engulfing
    is_bullish_engulfing = (
        prev['close'] < prev['open'] and
        last['close'] > last['open'] and
        last['close'] >= prev['open'] and
        last['open'] <= prev['close']
    )
    if is_bullish_engulfing:
        return {"pattern": "Bullish Engulfing", "type": "bullish"}

    # Bearish Engulfing
    is_bearish_engulfing = (
        prev['close'] > prev['open'] and
        last['close'] < last['open'] and
        last['close'] <= prev['open'] and
        last['open'] >= prev['close']
    )
    if is_bearish_engulfing:
        return {"pattern": "Bearish Engulfing", "type": "bearish"}

    # جسم اور وِکس کا حساب لگائیں
    body_size = abs(last['close'] - last['open'])
    total_range = last['high'] - last['low']
    
    # صفر تقسیم سے بچنے کے لیے جانچ
    if total_range == 0:
        return {"pattern": "کوئی حرکت نہیں", "type": "neutral"}

    # Doji
    if body_size / total_range < 0.1:
        return {"pattern": "Doji / غیر یقینی", "type": "neutral"}

    if last['close'] > last['open']:  # تیزی والی کینڈل
        upper_wick = last['high'] - last['close']
        lower_wick = last['open'] - last['low']
    else:  # مندی والی کینڈل
        upper_wick = last['high'] - last['open']
        lower_wick = last['close'] - last['low']

    # Hammer
    is_hammer = (lower_wick >= body_size * 2) and (upper_wick < body_size)
    if is_hammer:
        return {"pattern": "Hammer", "type": "bullish"}

    # Shooting Star
    is_shooting_star = (upper_wick >= body_size * 2) and (lower_wick < body_size)
    if is_shooting_star:
        return {"pattern": "Shooting Star", "type": "bearish"}

    return {"pattern": "کوئی خاص پیٹرن نہیں", "type": "neutral"}
    
