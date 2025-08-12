# filename: trainerai.py

import json
import logging
import threading
from typing import Dict, Any

from sqlalchemy.orm import Session

from models import ActiveSignal
from sentinel import check_news_at_time_of_trade

logger = logging.getLogger(__name__)

# ہم اب وزن کی فائل کو براہ راست یہاں استعمال نہیں کریں گے،
# لیکن فیڈ بیک لوپ کے لیے اسے محفوظ رکھیں گے
LEARNING_LOG_FILE = "learning_data.jsonl"
learning_lock = threading.Lock()

def get_confidence_score(
    technical_score: float,
    pattern_signal_type: str, 
    news_impact: str, 
    symbol_personality: Dict,
    core_signal: str
) -> float:
    """
    مختلف عوامل اور اثاثہ کی شخصیت کی بنیاد پر سگنل کے لیے ایک متحرک اعتماد کا اسکور تیار کرتا ہے۔
    """
    # تکنیکی اسکور کی بنیاد پر بنیادی اعتماد
    base_confidence = 50.0 + ((abs(technical_score) - 40) / 60 * 35) if abs(technical_score) >= 40 else 50.0
    
    multiplier = 1.0

    # 1. کینڈل اسٹک پیٹرن کا اثر
    if (core_signal == "buy" and pattern_signal_type == "bullish") or \
       (core_signal == "sell" and pattern_signal_type == "bearish"):
        multiplier *= 1.10  # 10% اضافہ
    elif (core_signal == "buy" and pattern_signal_type == "bearish") or \
         (core_signal == "sell" and pattern_signal_type == "bullish"):
        multiplier *= 0.90  # 10% کمی

    # 2. خبروں کا اثر (اثاثہ کی حساسیت کے ساتھ)
    if news_impact == "High":
        news_sensitivity = symbol_personality.get("news_sensitivity", 1.0)
        multiplier *= (1 - (0.15 * news_sensitivity)) # 1.0 کی حساسیت 15% کمی

    confidence = base_confidence * multiplier
    
    # حتمی اسکور کو 10 اور 99 کے درمیان محدود کریں
    confidence = max(10.0, min(99.0, confidence))
    
    return round(confidence, 2)

async def learn_from_outcome(db: Session, signal: ActiveSignal, outcome: str):
    """
    ٹریڈ کے نتیجے (TP/SL) کو اس کے تمام پیرامیٹرز کے ساتھ ایک لاگ فائل میں محفوظ کرتا ہے۔
    یہ ڈیٹا مستقبل میں مشین لرننگ ماڈل کو تربیت دینے کے لیے استعمال ہوگا۔
    """
    result_text = "کامیابی (TP Hit)" if outcome == "tp_hit" else "ناکامی (SL Hit)"
    logger.info(f"🧠 ٹرینر: فیڈ بیک موصول ہوا۔ {signal.symbol} پر نتیجہ: {result_text}۔ ڈیٹا محفوظ کیا جا رہا ہے...")

    try:
        # ٹریڈ کے دوران خبروں کی موجودگی کو چیک کریں
        trade_had_high_impact_news = await check_news_at_time_of_trade(
            signal.symbol, signal.created_at, signal.updated_at
        )

        # سیکھنے کے لیے ڈیٹا کا ایک جامع پیکج بنائیں
        learning_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "signal_id": signal.signal_id,
            "symbol": signal.symbol,
            "signal_type": signal.signal_type,
            "outcome": outcome,
            "confidence": signal.confidence,
            "strategy_type": signal.strategy_type, # یہ نیا اور اہم ہے
            "had_news": trade_had_high_impact_news,
            "entry_price": signal.entry_price,
            "tp_price": signal.tp_price,
            "sl_price": signal.sl_price,
            "close_price": signal.close_price,
            # مستقبل کے لیے: یہاں مزید انڈیکیٹر ویلیوز شامل کی جا سکتی ہیں
        }

        with learning_lock:
            with open(LEARNING_LOG_FILE, 'a') as f:
                f.write(json.dumps(learning_entry) + '\n')
        
        logger.info(f"🧠 سیکھنے کا ڈیٹا کامیابی سے '{LEARNING_LOG_FILE}' میں محفوظ کر دیا گیا۔")

    except Exception as e:
        logger.error(f"سیکھنے کے عمل کے دوران ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)

