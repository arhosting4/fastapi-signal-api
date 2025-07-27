# filename: trainerai.py

import random
from sqlalchemy.orm import Session
import database_crud as crud

def get_confidence(
    db: Session, 
    core_signal: str, 
    technical_score: float, # ★★★ نیا اور اہم پیرامیٹر ★★★
    pattern_signal_type: str, 
    risk_status: str, 
    news_impact: str, 
    symbol: str
) -> float:
    """
    ایک سگنل کے لیے اعتماد کا اسکور تیار کرتا ہے، جو تکنیکی اسکور، پیٹرن، رسک، اور ماضی کی کارکردگی پر مبنی ہوتا ہے۔
    """
    # 1. بنیادی اعتماد اب تکنیکی اسکور کی طاقت پر مبنی ہے
    # مثال: اسکور 40 (کم سے کم حد) پر 50% اعتماد، اور اسکور 100 (زیادہ سے زیادہ) پر 80% اعتماد
    # abs(technical_score) اس بات کو یقینی بناتا ہے کہ یہ buy اور sell دونوں کے لیے کام کرے
    base_confidence = 50 + ( (abs(technical_score) - 40) / 60 * 30 ) if abs(technical_score) >= 40 else 50
    
    # 2. ضرب دینے والے عوامل (Multipliers)
    multiplier = 1.0

    # پیٹرن کی تصدیق: اگر پیٹرن سگنل کی سمت میں ہے تو اعتماد بڑھائیں
    if (core_signal == "buy" and pattern_signal_type == "bullish") or \
       (core_signal == "sell" and pattern_signal_type == "bearish"):
        multiplier *= 1.15 # 15% اضافہ
    # اگر پیٹرن سگنل کے خلاف ہے تو اعتماد کم کریں
    elif (core_signal == "buy" and pattern_signal_type == "bearish") or \
         (core_signal == "sell" and pattern_signal_type == "bullish"):
        multiplier *= 0.85 # 15% کمی

    # رسک کی بنیاد پر اعتماد کو ایڈجسٹ کریں
    if risk_status == "Critical":
        multiplier *= 0.40 # 60% کمی
    elif risk_status == "High":
        multiplier *= 0.65 # 35% کمی
    elif risk_status == "Moderate":
        multiplier *= 0.90 # 10% کمی

    # خبروں کا اثر (یہ رسک کے علاوہ ایک اضافی چیک ہے)
    if news_impact == "High":
        multiplier *= 0.90 # اضافی 10% کمی

    # ماضی کی کارکردگی سے سیکھنا (Learning from past performance)
    feedback_stats = crud.get_feedback_stats_from_db(db, symbol)
    if feedback_stats and feedback_stats["total"] > 10: # کم از کم 10 ٹریڈز کے بعد سیکھنا شروع کریں
        accuracy = feedback_stats.get("accuracy", 50.0)
        # 50% درستگی پر 1.0 کا ضرب، 100% پر 1.2، 0% پر 0.8
        accuracy_multiplier = 0.80 + (accuracy / 250) # 0.8 سے 1.2 تک
        multiplier *= accuracy_multiplier

    # 3. حتمی اعتماد کا حساب لگائیں
    confidence = base_confidence * multiplier
    
    # اس بات کو یقینی بنائیں کہ اعتماد 10 اور 99 کے درمیان رہے
    confidence = max(10.0, min(99.0, confidence))
    
    return round(confidence, 2)
    
