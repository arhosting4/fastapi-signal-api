# filename: trainerai.py

import json
import logging
import threading
from typing import Dict, Any
from datetime import datetime  # <--- سب سے اہم اور شرمناک اصلاح

from sqlalchemy.orm import Session

from models import ActiveSignal
from sentinel import check_news_at_time_of_trade

logger = logging.getLogger(__name__)

LEARNING_DATA_FILE = "learning_data.json"
learning_lock = threading.Lock()

def get_confidence(
    db: Session, 
    core_signal: str, 
    technical_score: float,
    pattern_data: Dict[str, str], 
    news_impact: str, 
    symbol: str,
    symbol_personality: Dict
) -> float:
    """
    مختلف عوامل اور اثاثہ کی شخصیت کی بنیاد پر سگنل کے لیے ایک متحرک اعتماد کا اسکور تیار کرتا ہے۔
    """
    base_confidence = 50.0 + ((abs(technical_score) - 35) / 65 * 40) if abs(technical_score) >= 35 else 50.0
    
    multiplier = 1.0
    bonus = 0.0

    # 1. کینڈل اسٹک پیٹرن کا اثر
    pattern_type = pattern_data.get("type", "neutral")
    if (core_signal == "buy" and pattern_type == "bullish") or \
       (core_signal == "sell" and pattern_type == "bearish"):
        bonus += 5.0  # 5% کا بونس

    # 2. خبروں کا اثر (اثاثہ کی حساسیت کے ساتھ)
    if news_impact == "High":
        news_sensitivity = symbol_personality.get("news_sensitivity", 1.0)
        multiplier *= (1 - (0.15 * news_sensitivity)) # 15% کی کمی
    else:
        bonus += 5.0 # صاف خبروں پر 5% کا بونس

    confidence = (base_confidence * multiplier) + bonus
    confidence = max(10.0, min(99.0, confidence))
    
    return round(confidence, 2)

async def learn_from_outcome(db: Session, signal: ActiveSignal, outcome: str):
    """
    ٹریڈ کے نتیجے (TP/SL) سے سیکھتا ہے اور مستقبل کے فیصلوں کے لیے ڈیٹا محفوظ کرتا ہے۔
    """
    result_text = "کامیابی (TP Hit)" if outcome == "tp_hit" else "ناکامی (SL Hit)"
    logger.info(f"🧠 ٹرینر: فیڈ بیک موصول ہوا۔ {signal.symbol} پر نتیجہ: {result_text}۔ ڈیٹا محفوظ کیا جا رہا ہے...")

    try:
        trade_had_high_impact_news = await check_news_at_time_of_trade(
            signal.symbol, signal.created_at, datetime.utcnow()
        )

        learning_entry = {
            "signal_id": signal.signal_id,
            "symbol": signal.symbol,
            "outcome": outcome,
            "confidence": signal.confidence,
            "reason": signal.reason,
            "component_scores": signal.component_scores,
            "news_at_trade_time": trade_had_high_impact_news,
            "timestamp": datetime.utcnow().isoformat(),
        }

        with learning_lock:
            try:
                with open(LEARNING_DATA_FILE, 'r') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = []
            
            data.append(learning_entry)
            
            with open(LEARNING_DATA_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            
            logger.info(f"🧠 [{signal.symbol}] کا نتیجہ کامیابی سے لرننگ فائل میں محفوظ کر لیا گیا۔")

    except Exception as e:
        logger.error(f"سیکھنے کے عمل کے دوران ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        
