# filename: trainerai.py

import random
from sqlalchemy.orm import Session
import database_crud as crud

def get_confidence(db: Session, core_signal: str, pattern_signal_type: str, risk_status: str, news_impact: str, symbol: str, timeframe: str) -> float:
    """
    ★★★ خودکار اصلاح ★★★
    اعتماد کا حساب لگاتا ہے، اب یہ ٹائم فریم کی بنیاد پر فیڈ بیک کو بھی مدنظر رکھتا ہے۔
    """
    base_confidence = 50.0
    multiplier = 1.0

    # پیٹرن کی تصدیق
    if (core_signal == "buy" and pattern_signal_type == "bullish") or \
       (core_signal == "sell" and pattern_signal_type == "bearish"):
        multiplier *= 1.25
    elif pattern_signal_type != "neutral":
        multiplier *= 0.7

    # رسک کا اثر
    if risk_status == "High":
        multiplier *= 0.6
    elif risk_status == "Moderate":
        multiplier *= 0.85

    # خبروں کا اثر
    if news_impact == "High":
        multiplier *= 0.5

    # فیڈ بیک کی بنیاد پر ایکوریسی ملٹی پلائر (اب ٹائم فریم کے ساتھ)
    feedback_stats = crud.get_feedback_stats_from_db(db, symbol, timeframe) # <-- تبدیلی یہاں ہے
    if feedback_stats and feedback_stats["total"] > 10:
        accuracy = feedback_stats.get("accuracy", 50.0)
        # ایکوریسی کو 0.5 سے 1.5 کے درمیان ایک ملٹی پلائر میں تبدیل کریں
        accuracy_multiplier = 0.5 + (accuracy / 100)
        multiplier *= accuracy_multiplier

    confidence = base_confidence * multiplier
    
    # اعتماد کو 10 اور 99 کے درمیان محدود کریں
    confidence = max(10.0, min(99.0, confidence))
    
    return round(confidence, 2)
    
