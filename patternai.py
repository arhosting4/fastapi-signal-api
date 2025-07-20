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

    # تمام ضروری کالمز کو عددی قسم میں تبدیل کریں، غلطیوں کو NaN سے بدل دیں
    for col in required_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # کسی بھی نامکمل قطار کو ہٹا دیں
    df.dropna(inplace=True)
    
    # صفائی کے بعد دوبارہ ڈیٹا کی لمبائی چیک کریں
    if len(df) < 2:
        return {"pattern": "Insufficient Data after cleaning", "type": "neutral"}

    # 3. پیٹرن کی شناخت کے لیے آخری دو کینڈلز حاصل کریں
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # 4. پیٹرن کی شناخت کی منطق
    
    # --- Bullish Engulfing ---
    # پچھلی کینڈل سرخ (bearish) ہو، آخری کینڈل سبز (bullish) ہو
    # آخری کینڈل کا جسم پچھلی کینڈل کے جسم کو مکمل طور پر ڈھانپ لے
    is_bullish_engulfing = (prev['close'] < prev['open']) and \
                           (last['close'] > last['open']) and \
                           (last['close'] >= prev['open']) and \
                           (last['open'] <= prev['close'])
    if is_bullish_engulfing:
        return {"pattern": "Bullish Engulfing (Pure Python)", "type": "bullish"}

    # --- Bearish Engulfing ---
    # پچھلی کینڈل سبز (bullish) ہو، آخری کینڈل سرخ (bearish) ہو
    # آخری کینڈل کا جسم پچھلی کینڈل کے جسم کو مکمل طور پر ڈھانپ لے
    is_bearish_engulfing = (prev['close'] > prev['open']) and \
                           (last['close'] < last['open']) and \
                           (last['close'] <= prev['open']) and \
                           (last['open'] >= prev['close'])
    if is_bearish_engulfing:
        return {"pattern": "Bearish Engulfing (Pure Python)", "type": "bearish"}

    # --- Hammer اور Shooting Star کے لیے متغیرات ---
    body_size = abs(last['close'] - last['open'])
    
    # اگر جسم بہت چھوٹا ہے (Doji)، تو اسے نظر انداز کریں
    if body_size < (last['high'] - last['low']) * 0.05: # جسم کل رینج کے 5% سے کم ہے
        return {"pattern": "Doji-like / Indecision", "type": "neutral"}

    if last['close'] > last['open']: # Bullish candle
        upper_wick = last['high'] - last['close']
        lower_wick = last['open'] - last['low']
    else: # Bearish candle
        upper_wick = last['high'] - last['open']
        lower_wick = last['close'] - last['low']

    # --- Hammer (Bullish) ---
    # نچلا سایہ جسم سے کم از کم دوگنا ہو، اور اوپری سایہ بہت چھوٹا ہو
    is_hammer = (lower_wick >= body_size * 2) and (upper_wick < body_size)
    if is_hammer:
        return {"pattern": "Hammer (Pure Python)", "type": "bullish"}

    # --- Shooting Star (Bearish) ---
    # اوپری سایہ جسم سے کم از کم دوگنا ہو، اور نچلا سایہ بہت چھوٹا ہو
    is_shooting_star = (upper_wick >= body_size * 2) and (lower_wick < body_size)
    if is_shooting_star:
        return {"pattern": "Shooting Star (Pure Python)", "type": "bearish"}

    # 5. اگر کوئی پیٹرن نہ ملے
    return {"pattern": "No Specific Pattern", "type": "neutral"}
    
