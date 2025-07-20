# filename: patternai.py

import pandas as pd

def detect_patterns(candles: list) -> dict:
    """
    کینڈل اسٹک پیٹرنز کی شناخت کرتا ہے بغیر TA-Lib پر انحصار کیے۔
    یہ ایک سادہ، قابل اعتماد، اور مکمل طور پر درست شدہ نفاذ ہے۔
    """
    if not candles or len(candles) < 2:
        return {"pattern": "Insufficient Data", "type": "neutral"}

    df = pd.DataFrame(candles)
    
    required_cols = ['open', 'high', 'low', 'close']
    if not all(col in df.columns for col in required_cols):
        missing_cols = [col for col in required_cols if col not in df.columns]
        return {"pattern": f"Missing Columns: {', '.join(missing_cols)}", "type": "neutral"}

    for col in required_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df.dropna(inplace=True)
    if len(df) < 2:
        return {"pattern": "Insufficient Data after cleaning", "type": "neutral"}

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # --- پیٹرن کی شناخت کے لیے متغیرات کی تعریف ---
    body_size = abs(last['close'] - last['open'])
    
    # اس بات کو یقینی بنائیں کہ body_size صفر نہ ہو تاکہ تقسیم کی خرابی سے بچا جا سکے
    if body_size == 0:
        return {"pattern": "Doji / No Specific Pattern", "type": "neutral"}

    # --- اہم اصلاح: وِکس کی تعریف کو عالمی سطح پر منتقل کیا گیا ---
    if last['close'] > last['open']: # Bullish candle
        upper_wick = last['high'] - last['close']
        lower_wick = last['open'] - last['low']
    else: # Bearish candle
        upper_wick = last['high'] - last['open']
        lower_wick = last['close'] - last['low']

    # --- Bullish Engulfing ---
    if (prev['close'] < prev['open']) and (last['close'] > last['open']) and \
       (last['close'] >= prev['open']) and (last['open'] <= prev['close']):
        return {"pattern": "Bullish Engulfing (Pure Python)", "type": "bullish"}

    # --- Bearish Engulfing ---
    if (prev['close'] > prev['open']) and (last['close'] < last['open']) and \
       (last['close'] <= prev['open']) and (last['open'] >= prev['close']):
        return {"pattern": "Bearish Engulfing (Pure Python)", "type": "bearish"}

    # --- Hammer (Bullish) ---
    if lower_wick > body_size * 2 and upper_wick < body_size:
        return {"pattern": "Hammer (Pure Python)", "type": "bullish"}

    # --- Shooting Star (Bearish) ---
    if upper_wick > body_size * 2 and lower_wick < body_size:
        return {"pattern": "Shooting Star (Pure Python)", "type": "bearish"}

    return {"pattern": "No Specific Pattern", "type": "neutral"}
    
