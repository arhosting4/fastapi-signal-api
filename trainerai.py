# filename: trainerai.py

import logging
import json
import threading
import asyncio
from sqlalchemy.orm import Session
from typing import Dict, Any

from models import ActiveSignal
from sentinel import check_news_at_time_of_trade

logger = logging.getLogger(__name__)

WEIGHTS_FILE = "strategy_weights.json"
weights_lock = threading.Lock()

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
    تمام factors (tech score, pattern, risk, news) کی روشنی میں سگنل کا confidence score تیار کرے۔
    Complete compatibility, no external DB feedback used, just pure current metrics.
    """
    base_confidence = 50 + ((abs(technical_score) - 40) / 60 * 30) if abs(technical_score) >= 40 else 50
    multiplier = 1.0

    if (core_signal == "buy" and pattern_signal_type == "bullish") or (core_signal == "sell" and pattern_signal_type == "bearish"):
        multiplier *= 1.15
    elif (core_signal == "buy" and pattern_signal_type == "bearish") or (core_signal == "sell" and pattern_signal_type == "bullish"):
        multiplier *= 0.85

    if risk_status == "Critical":
        multiplier *= 0.40
    elif risk_status == "High":
        multiplier *= 0.65
    elif risk_status == "Moderate":
        multiplier *= 0.90

    if news_impact == "High":
        multiplier *= 0.90

    confidence = base_confidence * multiplier
    confidence = max(10.0, min(99.0, confidence))
    return round(confidence, 2)

async def learn_from_outcome(db: Session, signal: ActiveSignal, outcome: str):
    """
    ایک ٹریڈ کے نتیجے سے weights فائل کو ذہانت سے adapt کرے۔
    - outcome: "tp_hit" یا "sl_hit"
    - خبر کی موجودگی میں کم adjustment، ورنہ default
    """
    try:
        symbol = signal.symbol
        result = "کامیابی (TP Hit)" if outcome == "tp_hit" else "ناکامی (SL Hit)"
        logger.info(f"🧠 TR-AI: فیڈبیک ملا — {symbol} پر {result}")

        component_scores = signal.component_scores
        if not component_scores or not isinstance(component_scores, dict):
            logger.warning(f"{symbol} کیلئے component_scores غائب/غلط — سیکھنا skip")
            return

        adjustment_factor = 0.05
        if outcome == "sl_hit":
            trade_had_high_impact_news = await check_news_at_time_of_trade(
                symbol,
                signal.created_at,
                getattr(signal, 'updated_at', signal.created_at)
            )
            if trade_had_high_impact_news:
                logger.info(f"تجزیہ: ٹریڈ {symbol} خبروں کی وجہ سے ناکام — کم کمی کی جائے گی۔")
                adjustment_factor = 0.01
            else:
                logger.info(f"تجزیہ: ٹریڈ {symbol} بغیر خبر ناکام — normal کمی۔")

        with weights_lock:
            logger.info(f"{WEIGHTS_FILE} پر لاک لگا کر سیکھنے کا آغاز...")
            try:
                with open(WEIGHTS_FILE, 'r') as f:
                    weights = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                logger.error(f"{WEIGHTS_FILE} missing/corrupt — سیکھنا روک دیا گیا۔")
                return

            for component, score in component_scores.items():
                if component not in weights:
                    continue
                # صحیح direction میں prediction
                is_correct_direction = (signal.signal_type == "buy" and score > 0) or (signal.signal_type == "sell" and score < 0)
                if outcome == "tp_hit" and is_correct_direction:
                    weights[component] *= 1.05
                    logger.info(f"✅ [{component}] وزن 5% بڑھایا گیا!")
                elif outcome == "sl_hit" and is_correct_direction:
                    weights[component] *= (1 - adjustment_factor)
                    logger.info(f"❌ [{component}] وزن {adjustment_factor*100:.0f}% کم کیا گیا!")

            total_weight = sum(weights.values())
            if total_weight > 0:
                for k in weights:
                    weights[k] = round(max(0.05, min(0.5, weights[k] / total_weight)), 4)
            with open(WEIGHTS_FILE, 'w') as f:
                json.dump(weights, f, indent=4)
            logger.info(f"🧠 نئے weights save ہو گئے: {weights}")

    except Exception as e:
        logger.error(f"TR-AI learning error: {e}", exc_info=True)
    finally:
        if weights_lock.locked():
            weights_lock.release()
        logger.info("وزن کی فائل unlock کر دی گئی۔")
                
