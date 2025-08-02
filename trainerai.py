# filename: trainerai.py

import json
import logging
import threading
from typing import Dict, Any

from sqlalchemy.orm import Session

# مقامی امپورٹس
from models import ActiveSignal
from sentinel import check_news_at_time_of_trade

logger = logging.getLogger(__name__)

# --- مستقل اقدار ---
WEIGHTS_FILE = "strategy_weights.json"
# وزن کی فائل تک رسائی کو محفوظ بنانے کے لیے لاک
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
    مختلف عوامل کی بنیاد پر سگنل کے لیے ایک متحرک اعتماد کا اسکور تیار کرتا ہے۔
    """
    # بنیادی اعتماد کا اسکور تکنیکی اسکور کی طاقت پر مبنی ہے
    base_confidence = 50.0 + ((abs(technical_score) - 40) / 60 * 35) if abs(technical_score) >= 40 else 50.0
    
    multiplier = 1.0

    # 1. کینڈل اسٹک پیٹرن کا اثر
    if (core_signal == "buy" and pattern_signal_type == "bullish") or \
       (core_signal == "sell" and pattern_signal_type == "bearish"):
        multiplier *= 1.15  # موافق پیٹرن اعتماد کو بڑھاتا ہے
    elif (core_signal == "buy" and pattern_signal_type == "bearish") or \
         (core_signal == "sell" and pattern_signal_type == "bullish"):
        multiplier *= 0.85  # مخالف پیٹرن اعتماد کو کم کرتا ہے

    # 2. رسک کی حالت کا اثر
    if risk_status == "Critical":
        multiplier *= 0.40
    elif risk_status == "High":
        multiplier *= 0.65
    elif risk_status == "Moderate":
        multiplier *= 0.90

    # 3. خبروں کا اثر
    if news_impact == "High":
        multiplier *= 0.90 # اعلیٰ اثر والی خبریں غیر یقینی صورتحال پیدا کرتی ہیں

    # حتمی اعتماد کا حساب لگائیں اور اسے 10-99 کی حد میں رکھیں
    confidence = base_confidence * multiplier
    confidence = max(10.0, min(99.0, confidence))
    
    return round(confidence, 2)

async def learn_from_outcome(db: Session, signal: ActiveSignal, outcome: str):
    """
    ٹریڈ کے نتیجے (TP/SL) سے سیکھتا ہے اور حکمت عملی کے وزن کو ذہانت سے اپ ڈیٹ کرتا ہے۔
    یہ فنکشن پس منظر میں چلتا ہے۔
    """
    symbol = signal.symbol
    result_text = "کامیابی (TP Hit)" if outcome == "tp_hit" else "ناکامی (SL Hit)"
    logger.info(f"🧠 ٹرینر: فیڈ بیک موصول ہوا۔ {symbol} پر نتیجہ: {result_text}۔ وزن کو ایڈجسٹ کیا جا رہا ہے...")

    component_scores = signal.component_scores
    if not isinstance(component_scores, dict) or not component_scores:
        logger.warning(f"[{symbol}] کے لیے کوئی کمپوننٹ اسکور نہیں ملا۔ سیکھنے کا عمل روکا جا رہا ہے۔")
        return

    try:
        # ناکامی کی صورت میں ایڈجسٹمنٹ فیکٹر کا تعین کریں
        adjustment_factor = 0.05  # ڈیفالٹ کمی
        if outcome == "sl_hit":
            # چیک کریں کہ آیا ٹریڈ کے دوران کوئی اعلیٰ اثر والی خبر تھی
            trade_had_high_impact_news = await check_news_at_time_of_trade(
                symbol, signal.created_at, signal.updated_at
            )
            if trade_had_high_impact_news:
                logger.info(f"تجزیہ: ٹریڈ [{symbol}] خبروں کی وجہ سے ناکام ہو سکتی ہے۔ وزن میں کم کمی کی جائے گی۔")
                adjustment_factor = 0.01  # خبروں کی وجہ سے ناکامی پر کم سزا

        with weights_lock:
            logger.debug(f"وزن کی فائل ({WEIGHTS_FILE}) کو لاک کیا جا رہا ہے۔")
            try:
                with open(WEIGHTS_FILE, 'r') as f:
                    weights = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                logger.error(f"'{WEIGHTS_FILE}' نہیں ملی یا خراب ہے۔ سیکھنے کا عمل روکا جا رہا ہے۔")
                return

            # ہر جزو کے وزن کو ایڈجسٹ کریں
            for component, score in component_scores.items():
                if component not in weights:
                    continue

                # کیا جزو نے سگنل کی سمت کی صحیح پیش گوئی کی؟
                is_correct_prediction = (signal.signal_type == "buy" and score > 0) or \
                                        (signal.signal_type == "sell" and score < 0)

                if outcome == "tp_hit" and is_correct_prediction:
                    weights[component] *= (1 + 0.05) # انعام
                    logger.debug(f"✅ [{component}] کا وزن بڑھایا گیا (کامیاب پیش گوئی)۔")
                elif outcome == "sl_hit" and is_correct_prediction:
                    weights[component] *= (1 - adjustment_factor) # سزا
                    logger.debug(f"❌ [{component}] کا وزن {adjustment_factor*100:.0f}% کم کیا گیا (غلط پیش گوئی)۔")
            
            # وزن کو نارملائز کریں تاکہ ان کا مجموعہ 1 رہے
            total_weight = sum(weights.values())
            if total_weight > 0:
                weights = {key: value / total_weight for key, value in weights.items()}
            
            # وزن کو ایک محفوظ حد (0.05 سے 0.5) کے اندر رکھیں
            weights = {key: round(max(0.05, min(0.5, value)), 4) for key, value in weights.items()}

            # نئی وزن کو فائل میں محفوظ کریں
            with open(WEIGHTS_FILE, 'w') as f:
                json.dump(weights, f, indent=4)
            
            logger.info(f"🧠 نئے وزن کامیابی سے محفوظ کیے گئے: {weights}")

    except Exception as e:
        logger.error(f"سیکھنے کے عمل کے دوران ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    finally:
        if weights_lock.locked():
            weights_lock.release()
            logger.debug("وزن کی فائل کو ان لاک کر دیا گیا۔")
                
