# filename: patternai.py

from typing import Dict

import pandas as pd

def detect_patterns(df: pd.DataFrame) -> Dict[str, str]:
    """
    فراہم کردہ کینڈل اسٹک ڈیٹا فریم کی بنیاد پر عام کینڈل اسٹک پیٹرنز کی شناخت کرتا ہے۔
    
    Args:
        df (pd.DataFrame): کینڈل اسٹک ڈیٹا جس میں 'open', 'high', 'low', 'close' کالم ہوں۔
        
    Returns:
        Dict[str, str]: ایک ڈکشنری جس میں شناخت شدہ 'pattern' اور اس کی 'type' ('bullish', 'bearish', 'neutral') ہو۔
    """
    if len(df) < 2:
        return {"pattern": "ناکافی ڈیٹا", "type": "neutral"}

    # تجزیے کے لیے آخری دو کینڈلز کا استعمال کریں
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # --- Bullish پیٹرنز ---
    
    # Bullish Engulfing: ایک چھوٹی سرخ کینڈل کے بعد ایک بڑی سبز کینڈل جو پچھلی کینڈل کو مکمل طور پر نگل لے۔
    is_bullish_engulfing = (
        prev['close'] < prev['open'] and 
        last['close'] > last['open'] and 
        last['close'] >= prev['open'] and 
        last['open'] <= prev['close']
    )
    if is_bullish_engulfing:
        return {"pattern": "Bullish Engulfing", "type": "bullish"}

    # Hammer: ایک چھوٹی باڈی اور لمبا نچلا سایہ، جو نیچے کے رجحان کے بعد ممکنہ تبدیلی کی نشاندہی کرتا ہے۔
    body_size = abs(last['close'] - last['open'])
    total_range = last['high'] - last['low']
    if total_range == 0: # صفر سے تقسیم سے بچیں
        return {"pattern": "کوئی خاص پیٹرن نہیں", "type": "neutral"}
        
    lower_wick = (last['open'] if last['close'] > last['open'] else last['close']) - last['low']
    upper_wick = last['high'] - (last['close'] if last['close'] > last['open'] else last['open'])
    
    is_hammer = (lower_wick >= body_size * 2) and (upper_wick < body_size)
    if is_hammer:
        return {"pattern": "Hammer", "type": "bullish"}

    # --- Bearish پیٹرنز ---

    # Bearish Engulfing: ایک چھوٹی سبز کینڈل کے بعد ایک بڑی سرخ کینڈل جو پچھلی کینڈل کو مکمل طور پر نگل لے۔
    is_bearish_engulfing = (
        prev['close'] > prev['open'] and 
        last['close'] < last['open'] and 
        last['close'] <= prev['open'] and 
        last['open'] >= prev['close']
    )
    if is_bearish_engulfing:
        return {"pattern": "Bearish Engulfing", "type": "bearish"}

    # Shooting Star: ایک چھوٹی باڈی اور لمبا اوپری سایہ، جو اوپر کے رجحان کے بعد ممکنہ تبدیلی کی نشاندہی کرتا ہے۔
    is_shooting_star = (upper_wick >= body_size * 2) and (lower_wick < body_size)
    if is_shooting_star:
        return {"pattern": "Shooting Star", "type": "bearish"}

    # --- غیر جانبدار پیٹرنز ---

    # Doji: اوپن اور کلوز قیمتیں تقریباً برابر، جو غیر یقینی صورتحال کی نشاندہی کرتا ہے۔
    if body_size < total_range * 0.05:
        return {"pattern": "Doji/Indecision", "type": "neutral"}

    return {"pattern": "کوئی خاص پیٹرن نہیں", "type": "neutral"}
    
