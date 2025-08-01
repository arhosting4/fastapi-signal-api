# filename: patternai.py

import pandas as pd
from typing import Dict

def detect_patterns(df: pd.DataFrame) -> Dict[str, str]:
    """
    کینڈل اسٹک پیٹرنز کی شناخت کرتا ہے۔
    input: pandas DataFrame جس میں OHLC ڈیٹا ہو
    output: dict میں pattern کا نام اور type (bullish/bearish/neutral)
    """
    if df.empty or len(df) < 2:
        return {"pattern": "ناکافی ڈیٹا", "type": "neutral"}

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # --- 1. Bullish Engulfing ---
    is_bullish_engulfing = (
        prev['close'] < prev['open'] and
        last['close'] > last['open'] and
        last['close'] >= prev['open'] and
        last['open'] <= prev['close']
    )
    if is_bullish_engulfing:
        return {"pattern": "Bullish Engulfing", "type": "bullish"}

    # --- 2. Bearish Engulfing ---
    is_bearish_engulfing = (
        prev['close'] > prev['open'] and
        last['close'] < last['open'] and
        last['close'] <= prev['open'] and
        last['open'] >= prev['close']
    )
    if is_bearish_engulfing:
        return {"pattern": "Bearish Engulfing", "type": "bearish"}

    # --- 3. Doji / Indecision ---
    body_size = abs(last['close'] - last['open'])
    if (last['high'] - last['low']) == 0:
        return {"pattern": "کوئی خاص پیٹرن نہیں", "type": "neutral"}
    if body_size < (last['high'] - last['low']) * 0.05:
        return {"pattern": "Doji/Indecision", "type": "neutral"}

    # --- 4. Spinning Top or Basic Wick Checks ---
    if last['close'] > last['open']:
        upper_wick = last['high'] - last['close']
        lower_wick = last['open'] - last['low']
        if upper_wick > lower_wick * 1.5:
            return {"pattern": "Inverted Hammer", "type": "bullish"}
    else:
        upper_wick = last['high'] - last['open']
        lower_wick = last['close'] - last['low']
        if lower_wick > upper_wick * 1.5:
            return {"pattern": "Hammer", "type": "bullish"}

    # --- 5. Default Fallback ---
    return {"pattern": "کوئی نمایاں پیٹرن نہیں", "type": "neutral"}
