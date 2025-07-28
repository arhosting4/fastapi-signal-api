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

# ==============================================================================
# ★★★ کمک سیکھنے کا انجن (حتمی ورژن) ★★★
# ==============================================================================

# ★★★ یہ فنکشن اب مکمل اور درست ہے ★★★
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


def learn_from_outcome(db: Session, signal: ActiveSignal, outcome: str):
    """
    ٹریڈ کے نتیجے سے سیکھتا ہے اور strategy_weights.json کو اپ ڈیٹ کرتا ہے۔
    """
    try:
        symbol = signal.symbol
        result = "کامیابی (TP Hit)" if outcome == "tp_hit" else "ناکامی (SL Hit)"
        logger.info(f"🧠 ٹرینر نے فیڈ بیک وصول کیا: {symbol} پر نتیجہ {result} تھا۔")

        adjustment_factor = 0.05 # 5% ایڈجسٹمنٹ
        
        with weights_lock:
            logger.info(f"وزن کی فائل ({WEIGHTS_FILE}) کو لاک کیا جا رہا ہے۔")
            try:
                with open(WEIGHTS_FILE, 'r') as f:
                    weights = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                logger.error(f"{WEIGHTS_FILE} نہیں ملی۔ سیکھنے کا عمل روکا جا رہا ہے۔")
                return

            # ابھی کے لیے، ہم تمام وزن کو یکساں طور پر ایڈجسٹ کرتے ہیں۔
            # مستقبل میں، ہم سگنل کے ساتھ انفرادی انڈیکیٹر اسکور بھیج سکتے ہیں
            # تاکہ صرف متعلقہ وزن کو ایڈجسٹ کیا جا سکے۔
            if outcome == "tp_hit":
                logger.info(f"✅ {symbol} پر کامیاب ٹریڈ کی بنیاد پر حکمت عملی کو مضبوط کیا جا رہا ہے۔")
                for key in weights:
                    weights[key] *= (1 + adjustment_factor)
            else: # sl_hit
                logger.info(f"❌ {symbol} پر ناکام ٹریڈ کی بنیاد پر حکمت عملی کو ایڈجسٹ کیا جا رہا ہے۔")
                for key in weights:
                    weights[key] *= (1 - adjustment_factor)
            
            # وزن کو نارملائز کریں تاکہ ان کا مجموعہ 1 کے قریب رہے
            total_weight = sum(weights.values())
            if total_weight > 0:
                # نارملائزیشن کا فارمولا: ہر وزن کو کل وزن سے تقسیم کریں
                # اور پھر اسے کل وزن کے حساب سے ایڈجسٹ کریں تاکہ مجموعی اثر برقرار رہے
                # سادہ رکھنے کے لیے، ہم صرف اس بات کو یقینی بنائیں گے کہ وزن بہت زیادہ یا کم نہ ہو
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
            
