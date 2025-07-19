# filename: trainerai.py
import random
from sqlalchemy.orm import Session
import database_crud as crud

def get_confidence(db: Session, core_signal: str, pattern_signal_type: str, risk_status: str, news_impact: str, symbol: str) -> float:
    confidence = 55.0
    if core_signal == "buy" and pattern_signal_type == "bullish": confidence += 20
    elif core_signal == "sell" and pattern_signal_type == "bearish": confidence += 20
    elif (core_signal == "buy" and pattern_signal_type == "bearish") or (core_signal == "sell" and pattern_signal_type == "bullish"): confidence -= 25

    if risk_status == "High": confidence -= 20
    elif risk_status == "Moderate": confidence -= 5

    if news_impact == "High": confidence -= 20
    elif news_impact == "Medium": confidence -= 10

    feedback_stats = crud.get_feedback_stats_from_db(db, symbol)
    if feedback_stats and feedback_stats["total"] > 10:
        accuracy = feedback_stats.get("accuracy", 50.0)
        if accuracy > 70: confidence += 10
        elif accuracy < 40: confidence -= 15

    confidence = max(0.0, min(100.0, confidence))
    confidence += random.uniform(-2.0, 2.0)
    confidence = max(0.0, min(100.0, confidence))
    return round(confidence, 2)
    
