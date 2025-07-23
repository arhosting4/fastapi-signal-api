# filename: patternai.py

import pandas as pd

def detect_patterns(candles: list) -> dict:
    """
    کینڈل اسٹک پیٹرنز کی شناخت کرتا ہے بغیر TA-Lib پر انحصار کیے۔
    یہ ایک سادہ، قابل اعتماد، اور مکمل طور پر فعال نفاذ ہے۔
    """
    # 1. حفاظتی جانچ: کیا ہمارے پاس تجزیے کے لیے کافی ڈیٹا ہے؟
    if not candles or len(candles) < 2:
        return {"pattern": "Insufficient Data", "type": "neutral"}

    df = pd.DataFrame(candles)

    # 2. ڈیٹا کی صفائی اور توثیق
    required_cols = ['open', 'high', 'low', 'close']
    if not all(col in df.columns for col in required_cols):
        missing_cols = [col for col in required_cols if col not in df.columns]
        return {"pattern": f"Missing Columns: {', '.join(missing_cols)}", "type": "neutral"}

    for col in required_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df.dropna(inplace=True)

    if len(df) < 2:
        return {"pattern": "Insufficient Data after cleaning", "type": "neutral"}

    # 3. آخری دو کینڈلز حاصل کریں
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # 4. پیٹرن لاجک

    # Bullish Engulfing
    is_bullish_engulfing = (
        prev['close'] < prev['open'] and
        last['close'] > last['open'] and
        last['close'] >= prev['open'] and
        last['open'] <= prev['close']
    )
    if is_bullish_engulfing:
        return {"pattern": "Bullish Engulfing (Pure Python)", "type": "bullish"}

    # Bearish Engulfing
    is_bearish_engulfing = (
        prev['close'] > prev['open'] and
        last['close'] < last['open'] and
        last['close'] <= prev['open'] and
        last['open'] >= prev['close']
    )
    if is_bearish_engulfing:
        return {"pattern": "Bearish Engulfing (Pure Python)", "type": "bearish"}

    # Calculate body/wicks
    body_size = abs(last['close'] - last['open'])
    if body_size < (last['high'] - last['low']) * 0.05:
        return {"pattern": "Doji-like / Indecision", "type": "neutral"}

    if last['close'] > last['open']:  # Bullish
        upper_wick = last['high'] - last['close']
        lower_wick = last['open'] - last['low']
    else:  # Bearish
        upper_wick = last['high'] - last['open']
        lower_wick = last['close'] - last['low']

    # Hammer
    is_hammer = (lower_wick >= body_size * 2) and (upper_wick < body_size)
    if is_hammer:
        return {"pattern": "Hammer (Pure Python)", "type": "bullish"}

    # Shooting Star
    is_shooting_star = (upper_wick >= body_size * 2) and (lower_wick < body_size)
    if is_shooting_star:
        return {"pattern": "Shooting Star (Pure Python)", "type": "bearish"}

    # No pattern
    return {"pattern": "No Specific Pattern", "type": "neutral"}
