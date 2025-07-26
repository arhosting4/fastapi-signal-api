import pandas as pd
from typing import List, Dict

def detect_patterns(candles: List[Dict]) -> Dict[str, str]:
    """
    کینڈل اسٹک پیٹرنز کی شناخت کرتا ہے۔
    """
    if not candles or len(candles) < 2:
        return {"pattern": "ناکافی ڈیٹا", "type": "neutral"}

    # --- اہم تبدیلی: اب یہ پہلے سے ہی ڈکشنری ہے ---
    df = pd.DataFrame(candles)

    required_cols = ['open', 'high', 'low', 'close']
    if not all(col in df.columns for col in required_cols):
        return {"pattern": "کالم غائب ہیں", "type": "neutral"}

    for col in required_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.dropna(inplace=True)
    if len(df) < 2:
        return {"pattern": "ناکافی ڈیٹا", "type": "neutral"}

    last = df.iloc[-1]
    prev = df.iloc[-2]

    is_bullish_engulfing = (prev['close'] < prev['open'] and last['close'] > last['open'] and last['close'] >= prev['open'] and last['open'] <= prev['close'])
    if is_bullish_engulfing:
        return {"pattern": "Bullish Engulfing", "type": "bullish"}

    is_bearish_engulfing = (prev['close'] > prev['open'] and last['close'] < last['open'] and last['close'] <= prev['open'] and last['open'] >= prev['close'])
    if is_bearish_engulfing:
        return {"pattern": "Bearish Engulfing", "type": "bearish"}

    body_size = abs(last['close'] - last['open'])
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
    
