# filename: trainerai.py

import logging
import threading
from sqlalchemy.orm import Session
from typing import Dict
from models import ActiveSignal
from sentinel import check_news_at_time_of_trade

logger = logging.getLogger(__name__)
weights_lock = threading.Lock()

# =====================================================================================
def calculate_base_confidence(technical_score: float) -> float:
    if abs(technical_score) >= 40:
        return 50 + ((abs(technical_score) - 40) / 60 * 30)
    return 50

def pattern_multiplier(core_signal: str, pattern_type: str) -> float:
    if (core_signal == "buy" and pattern_type == "bullish") or \
       (core_signal == "sell" and pattern_type == "bearish"):
        return 1.15
    elif (core_signal == "buy" and pattern_type == "bearish") or \
         (core_signal == "sell" and pattern_type == "bullish"):
        return 0.85
    return 1.0

def risk_multiplier(risk_status: str) -> float:
    if risk_status.lower() in ["low", "moderate"]:
        return 1.10
    elif risk_status.lower() == "high":
        return 0.85
    return 1.0

def news_multiplier(news_impact: str) -> float:
    if news_impact.lower() == "positive":
        return 1.10
    elif news_impact.lower() == "negative":
        return 0.85
    return 1.0

# =====================================================================================
def get_confidence(
    db: Session,
    core_signal: str,
    technical_score: float,
    pattern_signal_type: str,
    risk_status: str,
    news_impact: str,
    symbol: str
) -> float:
    """
    مختلف عوامل کی بنیاد پر سگنل کے لیے اعتماد (confidence) کا حساب لگاتا ہے۔
    اس میں شامل ہیں: تکنیکی سکور، پیٹرن، خطرہ، اور نیوز کا اثر۔
    """

    base_conf = calculate_base_confidence(technical_score)

    pattern_mult = pattern_multiplier(core_signal, pattern_signal_type)
    risk_mult = risk_multiplier(risk_status)
    news_mult = news_multiplier(news_impact)

    final_score = base_conf * pattern_mult * risk_mult * news_mult
    confidence = round(min(final_score, 100), 2)

    logger.info(f"🔍 Confidence generated for {symbol} = {confidence}")
    return confidence
