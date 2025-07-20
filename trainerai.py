# filename: trainerai.py

import random
from sqlalchemy.orm import Session
import database_crud as crud

def get_confidence(db: Session, core_signal: str, pattern_signal_type: str, risk_status: str, news_impact: str, symbol: str) -> float:
    """
    سگنل کے اعتماد کا تخمینہ لگاتا ہے، جس میں ڈیٹا بیس سے فیڈ بیک شامل ہے۔
    """
    confidence = 55.0

    # 1. بنیادی سگنل اور پیٹرن کی مطابقت
    if core_signal == "buy" and pattern_signal_type == "bullish":
        confidence += 20
    elif core_signal == "sell" and pattern_signal_type == "bearish":
        confidence += 20
    elif (core_signal == "buy" and pattern_signal_type == "bearish") or \
         (core_signal == "sell" and pattern_signal_type == "bullish"):
        confidence -= 25

    # 2. رسک کی تشخیص کا اثر
    if risk_status == "High":
        confidence -= 20
    elif risk_status == "Moderate":
        confidence -= 10

    # 3. خبروں کے اثرات کی تشخیص
    if news_impact == "High":
        confidence -= 20
    elif news_impact == "Medium":
        confidence -= 10

    # 4. فیڈ بیک لوپ کا اثر (ڈیٹا بیس سے)
    # --- اہم تبدیلی: غلط فنکشن نام کو درست کیا گیا ---
    feedback_stats = crud.get_feedback_stats_from_db(db, symbol)
    if feedback_stats and feedback_stats["total"] > 10:
        accuracy = feedback_stats.get("accuracy", 50.0)
        if accuracy > 70:
            confidence += 10
        elif accuracy < 40:
            confidence -= 15

    # اعتماد کو 0-100 کی حد میں رکھیں
    confidence = max(0.0, min(100.0, confidence))
    confidence += random.uniform(-1.5, 1.5) # تھوڑا سا بے ترتیب پن
    confidence = max(0.0, min(100.0, confidence))

    return round(confidence, 2)
    
