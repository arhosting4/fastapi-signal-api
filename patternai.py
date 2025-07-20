# filename: patternai.py

import pandas as pd
# --- اہم تبدیلی: pandas_ta کو اب صرف ان فنکشنز کے لیے استعمال کیا جائے گا جو TA-Lib پر انحصار نہیں کرتے ---
# ہم کینڈل اسٹک پیٹرنز کو خود نافذ کریں گے

def detect_patterns(candles: list) -> dict:
    """
    کینڈل اسٹک پیٹرنز کی شناخت کرتا ہے بغیر TA-Lib پر انحصار کیے۔
    یہ ایک سادہ لیکن قابل اعتماد نفاذ ہے۔
    """
    if not candles or len(candles) < 2:
        return {"pattern": "Insufficient Data", "type": "neutral"}

    df = pd.DataFrame(candles)
    # یقینی بنائیں کہ کالمز عددی ہیں
    for col in ['open', 'high', 'low', 'close']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        else:
            # اگر کوئی ضروری کالم غائب ہے تو باہر نکل جائیں
            return {"pattern": f"Missing Column: {col}", "type": "neutral"}
    
    df.dropna(inplace=True)
    if len(df) < 2:
        return {"pattern": "Insufficient Data after cleaning", "type": "neutral"}

    # آخری دو کینڈلز حاصل کریں
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # --- Bullish Engulfing ---
    # پچھلی کینڈل سرخ ہو، آخری کینڈل سبز ہو
    # آخری کینڈل کا جسم پچھلی کینڈل کے جسم کو مکمل طور پر ڈھانپ لے
    if (prev['close'] < prev['open']) and (last['close'] > last['open']) and \
       (last['close'] >= prev['open']) and (last['open'] <= prev['close']):
        return {"pattern": "Bullish Engulfing (Pure Python)", "type": "bullish"}

    # --- Bearish Engulfing ---
    # پچھلی کینڈل سبز ہو، آخری کینڈل سرخ ہو
    # آخری کینڈل کا جسم پچھلی کینڈل کے جسم کو مکمل طور پر ڈھانپ لے
    if (prev['close'] > prev['open']) and (last['close'] < last['open']) and \
       (last['close'] <= prev['open']) and (last['open'] >= prev['close']):
        return {"pattern": "Bearish Engulfing (Pure Python)", "type": "bearish"}

    # --- Hammer (Bullish) ---
    # چھوٹا جسم، لمبا نچلا سایہ، بہت چھوٹا یا کوئی اوپری سایہ نہیں
    body_size = abs(last['close'] - last['open'])
    lower_wick = last['open'] - last['low'] if last['close'] > last['open'] else last['close'] - last['low']
    upper_wick = last['high'] - last['close'] if last['close'] > last['open'] else last['high'] - last['open']
    
    if lower_wick > body_size * 2 and upper_wick < body_size * 0.5 and body_size > 0:
        return {"pattern": "Hammer (Pure Python)", "type": "bullish"}

    # --- Shooting Star (Bearish) ---
    # چھوٹا جسم، لمبا اوپری سایہ، بہت چھوٹا یا کوئی نچلا سایہ نہیں
    if upper_wick > body_size * 2 and lower_wick < body_size * 0.5 and body_size > 0:
        return {"pattern": "Shooting Star (Pure Python)", "type": "bearish"}

    return {"pattern": "No Specific Pattern", "type": "neutral"}
    
