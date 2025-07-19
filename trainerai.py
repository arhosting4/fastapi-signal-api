# trainerai.py

import random
from typing import List

# --- نئی تبدیلی: ڈیٹا بیس کے لیے امپورٹس ---
from sqlalchemy.orm import Session
from src.database.models import FeedbackEntry

# --- نئی تبدیلی: یہ فنکشن اب ڈیٹا بیس سیشن لے گا ---
def get_feedback_stats_from_db(db: Session, symbol: str) -> dict:
    """ڈیٹا بیس سے فیڈ بیک کے اعداد و شمار حاصل کرتا ہے۔"""
    feedback_query = db.query(FeedbackEntry).filter(FeedbackEntry.symbol == symbol).all()
    
    if not feedback_query:
        return {"total": 0, "accuracy": None, "correct": 0, "incorrect": 0, "missed": 0}

    total = len(feedback_query)
    correct = sum(1 for f in feedback_query if f.feedback == "correct")
    incorrect = sum(1 for f in feedback_query if f.feedback == "incorrect")
    missed = sum(1 for f in feedback_query if f.feedback == "missed")

    accuracy = (correct / total) * 100 if total > 0 else None

    return {
        "total": total,
        "correct": correct,
        "incorrect": incorrect,
        "missed": missed,
        "accuracy": round(accuracy, 2) if accuracy is not None else None
    }

# --- نئی تبدیلی: یہ فنکشن بھی اب ڈیٹا بیس سیشن لے گا ---
def get_confidence(
    db: Session, #<-- نیا پیرامیٹر
    core_signal: str,
    pattern_signal_type: str,
    risk_status: str,
    news_impact: str,
    symbol: str
) -> float:
    """سگنل کے اعتماد کا تخمینہ لگاتا ہے۔"""
    confidence = 55.0

    if core_signal == "buy" and pattern_signal_type == "bullish":
        confidence += 20
    elif core_signal == "sell" and pattern_signal_type == "bearish":
        confidence += 20
    elif (core_signal == "buy" and pattern_signal_type == "bearish") or \
         (core_signal == "sell" and pattern_signal_type == "bullish"):
        confidence -= 25

    if risk_status == "High":
        confidence -= 20
    elif risk_status == "Moderate":
        confidence -= 5

    if news_impact == "High":
        confidence -= 20
    elif news_impact == "Medium":
        confidence -= 10

    # --- نئی تبدیلی: فیڈ بیک ڈیٹا بیس سے حاصل کریں ---
    feedback = get_feedback_stats_from_db(db, symbol)
    if feedback and feedback["total"] > 10:
        accuracy = feedback.get("accuracy", 50)
        if accuracy > 70:
            confidence += 10
        elif accuracy < 40:
            confidence -= 15

    confidence = max(0.0, min(100.0, confidence))
    confidence += random.uniform(-2.0, 2.0)
    confidence = max(0.0, min(100.0, confidence))

    return round(confidence, 2)
    
