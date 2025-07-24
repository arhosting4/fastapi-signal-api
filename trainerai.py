# filename: trainerai.py
import random
from sqlalchemy.orm import Session
import database_crud as crud

def get_confidence(
    db: Session,
    core_signal: str,
    pattern_signal_type: str,
    risk_status: str,
    news_impact: str,
    symbol: str
) -> float:
    """
    سگنل کے اعتماد کا تخمینہ لگاتا ہے، جس میں ڈیٹا بیس سے فیڈ بیک شامل ہے۔
    """
    # بنیادی اعتماد 50 سے شروع ہوتا ہے
    confidence = 50.0

    # 1. بنیادی سگنل اور پیٹرن کی مطابقت
    if core_signal == "buy" and pattern_signal_type == "bullish":
        confidence += 15
    elif core_signal == "sell" and pattern_signal_type == "bearish":
        confidence += 15
    elif (core_signal == "buy" and pattern_signal_type == "bearish") or \
         (core_signal == "sell" and pattern_signal_type == "bullish"):
        confidence -= 20 # مضبوط منفی اشارہ

    # 2. رسک کی تشخیص کا اثر
    if risk_status == "High":
        confidence -= 20
    elif risk_status == "Moderate":
        confidence -= 10

    # 3. خبروں کے اثرات کی تشخیص
    if news_impact == "High":
        confidence -= 25 # خبروں کا اثر سب سے زیادہ ہے

    # 4. فیڈ بیک لوپ کا اثر (ڈیٹا بیس سے)
    feedback_stats = crud.get_feedback_stats_from_db(db, symbol)
    if feedback_stats and feedback_stats["total"] > 10: # کم از کم 10 ٹریڈز کے بعد سیکھیں
        accuracy = feedback_stats.get("accuracy", 50.0)
        if accuracy > 75:
            confidence += 15 # اعلیٰ درستگی پر بڑا انعام
        elif accuracy > 60:
            confidence += 7
        elif accuracy < 40:
            confidence -= 15 # کم درستگی پر بڑی سزا

    # اعتماد کو 10-99 کی حد میں رکھیں
    confidence = max(10.0, min(99.0, confidence))
    
    # تھوڑا سا بے ترتیب پن تاکہ ہر بار ایک جیسی قدر نہ آئے
    confidence += random.uniform(-1.0, 1.0)
    confidence = max(10.0, min(99.0, confidence))

    return round(confidence, 2)
    
