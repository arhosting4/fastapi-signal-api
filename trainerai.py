# filename: trainerai.py
import random
from sqlalchemy.orm import Session
import database_crud as crud

def get_confidence(db: Session, core_signal: str, pattern_signal_type: str, risk_status: str, news_impact: str, symbol: str) -> float:
    base_confidence = 50.0
    multiplier = 1.0

    if (core_signal == "buy" and pattern_signal_type == "bullish") or (core_signal == "sell" and pattern_signal_type == "bearish"):
        multiplier *= 1.25
    elif pattern_signal_type != "neutral":
        multiplier *= 0.7

    if risk_status == "High":
        multiplier *= 0.6
    elif risk_status == "Moderate":
        multiplier *= 0.85

    if news_impact == "High":
        multiplier *= 0.5

    feedback_stats = crud.get_feedback_stats_from_db(db, symbol)
    if feedback_stats and feedback_stats["total"] > 10:
        accuracy = feedback_stats.get("accuracy", 50.0)
        accuracy_multiplier = 0.5 + (accuracy / 100)
        multiplier *= accuracy_multiplier

    confidence = base_confidence * multiplier
    confidence = max(10.0, min(99.0, confidence))
    
    return round(confidence, 2)
