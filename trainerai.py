# filename: trainerai.py

import random
import logging
import json
import threading
from sqlalchemy.orm import Session
from typing import Dict, Any

import database_crud as crud
from models import ActiveSignal

logger = logging.getLogger(__name__)
WEIGHTS_FILE = "strategy_weights.json"
weights_lock = threading.Lock() # فائل تک رسائی کو محفوظ بنانے کے لیے

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
    مختلف عوامل کی بنیاد پر سگنل کے لیے اعتماد کا اسکور تیار کرتا ہے۔
    """
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

# ★★★ مکمل طور پر نیا اور ذہین سیکھنے کا فنکشن ★★★
def learn_from_outcome(db: Session, signal: ActiveSignal, outcome: str):
    """
    ٹریڈ کے نتیجے سے سیکھتا ہے اور strategy_weights.json کو ذہانت سے اپ ڈیٹ کرتا ہے۔
    یہ فنکشن اب ہر انڈیکیٹر کے انفرادی کردار کی بنیاد پر وزن کو ایڈجسٹ کرتا ہے۔
    """
    try:
        symbol = signal.symbol
        result = "کامیابی (TP Hit)" if outcome == "tp_hit" else "ناکامی (SL Hit)"
        logger.info(f"🧠 ٹرینر نے فیڈ بیک وصول کیا: {symbol} پر نتیجہ {result} تھا۔")

        component_scores = signal.component_scores
        if not component_scores or not isinstance(component_scores, dict):
            logger.warning(f"{symbol} کے لیے کوئی کمپوننٹ اسکور نہیں ملا۔ سیکھنے کا عمل روکا جا رہا ہے۔")
            return

        adjustment_factor = 0.05 # 5% ایڈجسٹمنٹ
        
        with weights_lock:
            logger.info(f"وزن کی فائل ({WEIGHTS_FILE}) کو لاک کیا جا رہا ہے۔")
            try:
                with open(WEIGHTS_FILE, 'r') as f:
                    weights = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                logger.error(f"{WEIGHTS_FILE} نہیں ملی یا خراب ہے۔ سیکھنے کا عمل روکا جا رہا ہے۔")
                return

            # ہر کمپوننٹ کا انفرادی طور پر جائزہ لیں
            for component, score in component_scores.items():
                weight_key = component # e.g., "ema_cross", "rsi_position"
                if weight_key not in weights:
                    continue

                is_correct_prediction = (signal.signal_type == "buy" and score > 0) or \
                                        (signal.signal_type == "sell" and score < 0)

                # اگر نتیجہ کامیاب تھا اور انڈیکیٹر نے صحیح پیش گوئی کی، تو اس کا وزن بڑھائیں
                if outcome == "tp_hit" and is_correct_prediction:
                    weights[weight_key] *= (1 + adjustment_factor)
                    logger.info(f"✅ [{weight_key}] کا وزن بڑھایا گیا کیونکہ اس نے کامیاب ٹریڈ کی صحیح پیش گوئی کی تھی۔")
                # اگر نتیجہ ناکام تھا اور انڈیکیٹر نے (غلط) پیش گوئی کی، تو اس کا وزن کم کریں
                elif outcome == "sl_hit" and is_correct_prediction:
                    weights[weight_key] *= (1 - adjustment_factor)
                    logger.info(f"❌ [{weight_key}] کا وزن کم کیا گیا کیونکہ اس نے ناکام ٹریڈ کی غلط پیش گوئی کی تھی۔")
            
            # وزن کو نارملائز کریں تاکہ ان کا مجموعہ 1 کے قریب رہے
            total_weight = sum(weights.values())
            if total_weight > 0:
                for key in weights:
                    weights[key] = weights[key] / total_weight
            
            # ہر وزن کو ایک خاص حد کے اندر رکھیں
            for key, value in weights.items():
                weights[key] = round(max(0.05, min(0.5, value)), 4)

            with open(WEIGHTS_FILE, 'w') as f:
                json.dump(weights, f, indent=4)
            
            logger.info(f"🧠 نئے وزن کامیابی سے محفوظ کیے گئے: {weights}")

    except Exception as e:
        logger.error(f"سیکھنے کے عمل کے دوران خرابی: {e}", exc_info=True)
    finally:
        if weights_lock.locked():
            weights_lock.release()
            logger.info("وزن کی فائل کو ان لاک کر دیا گیا۔")
                    
