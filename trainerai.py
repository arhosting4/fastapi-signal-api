# filename: trainerai.py

import random
from sqlalchemy.orm import Session
import database_crud as crud

def get_confidence(
    db: Session, 
    core_signal: str, 
    technical_score: float,
    pattern_signal_type: str, 
    risk_status: str, 
    news_impact: str, 
    symbol: str
) -> float:
    base_confidence = 50 + ( (abs(technical_score) - 40) / 60 * 30 ) if abs(technical_score) >= 40 else 50
    
    multiplier = 1.0

    if (core_signal == "buy" and pattern_signal_type == "bullish") or \
       (core_signal == "sell" and pattern_signal_type == "bearish"):
        multiplier *= 1.15
    elif (core_signal == "buy" and pattern_signal_type == "bearish") or \
         (core_signal == "sell" and pattern_signal_type == "bullish"):
        multiplier *= 0.85

    if risk_status == "Critical":
        multiplier *= 0.40
    elif risk_status == "High":
        multiplier *= 0.65
    elif risk_status == "Moderate":
        multiplier *= 0.90

    if news_impact == "High":
        multiplier *= 0.90

    feedback_stats = crud.get_feedback_stats_from_db(db, symbol)
    if feedback_stats and feedback_stats["total"] > 10:
        accuracy = feedback_stats.get("accuracy", 50.0)
        accuracy_multiplier = 0.80 + (accuracy / 250)
        multiplier *= accuracy_multiplier

    confidence = base_confidence * multiplier
    
    confidence = max(10.0, min(99.0, confidence))
    
    return round(confidence, 2)
    
