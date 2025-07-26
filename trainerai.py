# filename: trainerai.py
import random
from sqlalchemy.orm import Session
import database_crud as crud

def get_confidence(db: Session, core_signal: str, pattern_signal_type: str, risk_status: str, news_impact: str, symbol: str) -> float:
    base_confidence = 60.0  # بنیادی اعتماد کو تھوڑا بڑھایا گیا
    multiplier = 1.0

    # پیٹرن کی تصدیق
    if (core_signal == "buy" and pattern_signal_type == "bullish") or (core_signal == "sell" and pattern_signal_type == "bearish"):
        multiplier *= 1.20 # 20% اضافہ
    elif pattern_signal_type != "neutral":
        multiplier *= 0.80 # 20% کمی

    # ★★★ نئی رسک منطق ★★★
    if risk_status == "Critical":
        multiplier *= 0.40 # 60% کمی
    elif risk_status == "High":
        multiplier *= 0.60 # 40% کمی
    elif risk_status == "Moderate":
        multiplier *= 0.85 # 15% کمی

    # خبروں کا اثر (یہ رسک اسٹیٹس میں شامل ہے، لیکن اضافی کمی بھی کر سکتے ہیں)
    if news_impact == "High":
        multiplier *= 0.90 # اضافی 10% کمی

    # ماضی کی کارکردگی سے سیکھنا
    feedback_stats = crud.get_feedback_stats_from_db(db, symbol)
    if feedback_stats and feedback_stats["total"] > 10:
        accuracy = feedback_stats.get("accuracy", 50.0)
        # 50% درستگی پر 1.0 کا ضرب، 100% پر 1.25، 0% پر 0.75
        accuracy_multiplier = 0.75 + (accuracy / 200) 
        multiplier *= accuracy_multiplier

    confidence = base_confidence * multiplier
    confidence = max(10.0, min(99.0, confidence))
    
    return round(confidence, 2)
    
