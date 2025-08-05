# filename: trainerai.py

import json
import logging
import threading
from typing import Dict, Any

from sqlalchemy.orm import Session

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
    news_impact: str, 
    symbol: str,
    symbol_personality: Dict
) -> float:
    """
    مختلف عوامل اور اثاثہ کی شخصیت کی بنیاد پر سگنل کے لیے ایک متحرک اعتماد کا اسکور تیار کرتا ہے۔
    """
    base_confidence = 50.0 + ((abs(technical_score) - 40) / 60 * 35) if abs(technical_score) >= 40 else 50.0
    
    multiplier = 1.0

    # 1. کینڈل اسٹک پیٹرن کا اثر
    if (core_signal == "buy" and pattern_signal_type == "bullish") or \
       (core_signal == "sell" and pattern_signal_type == "bearish"):
        multiplier *= 1.10
    elif (core_signal == "buy" and pattern_signal_type == "bearish") or \
         (core_signal == "sell" and pattern_signal_type == "bullish"):
        multiplier *= 0.90

    # 2. خبروں کا اثر (اثاثہ کی حساسیت کے ساتھ)
    if news_impact == "High":
        news_sensitivity = symbol_personality.get("news_sensitivity", 1.0)
        multiplier *= (1 - (0.1 * news_sensitivity)) # 1.0 کی حساسیت 10% کمی، 1.8 کی حساسیت 18% کمی

    confidence = base_confidence * multiplier
    confidence = max(10.0, min(99.0, confidence))
    
    return round(confidence, 2)

async def learn_from_outcome(db: Session, signal: ActiveSignal, outcome: str):
    """
    ٹریڈ کے نتیجے (TP/SL) سے سیکھتا ہے اور حکمت عملی کے وزن کو ذہانت سے اپ ڈیٹ کرتا ہے۔
    """
    symbol = signal.symbol
    result_text = "کامیابی (TP Hit)" if outcome == "tp_hit" else "ناکامی (SL Hit)"
    logger.info(f"🧠 ٹرینر: فیڈ بیک موصول ہوا۔ {symbol} پر نتیجہ: {result_text}۔ وزن کو ایڈجسٹ کیا جا رہا ہے...")

    component_scores = signal.component_scores
    if not isinstance(component_scores, dict) or not component_scores:
        logger.warning(f"[{symbol}] کے لیے کوئی کمپوننٹ اسکور نہیں ملا۔ سیکھنے کا عمل روکا جا رہا ہے۔")
        return

    try:
        adjustment_factor = 0.05
        if outcome == "sl_hit":
            trade_had_high_impact_news = await check_news_at_time_of_trade(
                symbol, signal.created_at, signal.updated_at
            )
            if trade_had_high_impact_news:
                logger.info(f"تجزیہ: ٹریڈ [{symbol}] خبروں کی وجہ سے ناکام ہو سکتی ہے۔ وزن میں کم کمی کی جائے گی۔")
                adjustment_factor = 0.01

        with weights_lock:
            logger.debug(f"وزن کی فائل ({WEIGHTS_FILE}) کو لاک کیا جا رہا ہے۔")
            try:
                with open(WEIGHTS_FILE, 'r') as f:
                    weights = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                logger.error(f"'{WEIGHTS_FILE}' نہیں ملی یا خراب ہے۔ سیکھنے کا عمل روکا جا رہا ہے۔")
                return

            for component, score in component_scores.items():
                if component not in weights:
                    continue

                is_correct_prediction = (signal.signal_type == "buy" and score > 0) or \
                                        (signal.signal_type == "sell" and score < 0)

                if outcome == "tp_hit" and is_correct_prediction:
                    weights[component] *= (1 + 0.05)
                    logger.debug(f"✅ [{component}] کا وزن بڑھایا گیا (کامیاب پیش گوئی)۔")
                elif outcome == "sl_hit" and is_correct_prediction:
                    weights[component] *= (1 - adjustment_factor)
                    logger.debug(f"❌ [{component}] کا وزن {adjustment_factor*100:.0f}% کم کیا گیا (غلط پیش گوئی)۔")
            
            total_weight = sum(weights.values())
            if total_weight > 0:
                weights = {key: value / total_weight for key, value in weights.items()}
            
            weights = {key: round(max(0.05, min(0.5, value)), 4) for key, value in weights.items()}

            with open(WEIGHTS_FILE, 'w') as f:
                json.dump(weights, f, indent=4)
            
            logger.info(f"🧠 نئے وزن کامیابی سے محفوظ کیے گئے: {weights}")

    except Exception as e:
        logger.error(f"سیکھنے کے عمل کے دوران ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    finally:
        if weights_lock.locked():
            weights_lock.release()
            logger.debug("وزن کی فائل کو ان لاک کر دیا گیا۔")
                    
