import asyncio
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

# مقامی امپورٹس
from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import generate_final_signal
from signal_tracker import add_active_signal, get_active_signals_count
from messenger import send_telegram_alert
from models import SessionLocal
from websocket_manager import manager # <-- نیا امپورٹ

logger = logging.getLogger(__name__)

# کنفیگریشن
MAX_ACTIVE_SIGNALS = 5
FINAL_CONFIDENCE_THRESHOLD = 60.0

async def analyze_pair(db: Session, pair: str) -> Optional[Dict[str, Any]]:
    """ایک تجارتی جوڑے کا تجزیہ کرتا ہے اور اگر کوئی سگنل ملے تو اسے واپس کرتا ہے۔"""
    logger.info(f"[{pair}] کے لیے کینڈل ڈیٹا حاصل کیا جا رہا ہے...")
    candles = await fetch_twelve_data_ohlc(pair)
    if not candles or len(candles) < 34:
        logger.warning(f"[{pair}] کے لیے ناکافی کینڈل ڈیٹا ({len(candles) if candles else 0})۔")
        return None

    logger.info(f"[{pair}] کے لیے AI فیوژن انجن چلایا جا رہا ہے...")
    signal_result = await generate_final_signal(db, pair, candles)
    
    if signal_result and signal_result.get("status") == "ok":
        return signal_result
    elif signal_result:
        logger.info(f"[{pair}] کے لیے کوئی سگنل نہیں بنا۔ وجہ: {signal_result.get('reason', 'نامعلوم')}")
    
    return None

async def hunt_for_signals_job():
    """
    سگنل کی تلاش کا مرکزی کام جو شیڈیولر کے ذریعے چلایا جاتا ہے۔
    """
    logger.info("=============================================")
    logger.info(">>> سگنل کی تلاش کا کام (Hunt Job) شروع ہو رہا ہے...")
    logger.info("=============================================")

    if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
        logger.info("فعال سگنلز کی زیادہ سے زیادہ حد تک پہنچ گئے ہیں۔ شکار روکا جا رہا ہے۔")
        return

    pairs = get_available_pairs()
    logger.info(f"تجزیہ کے لیے دستیاب جوڑے: {pairs}")
    db = SessionLocal()
    
    try:
        for pair in pairs:
            if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
                logger.info("سگنل کی حد تک پہنچ گئے۔ شکار روکا جا رہا ہے۔")
                break
            
            result = await analyze_pair(db, pair)

            if result and result.get("confidence", 0) >= FINAL_CONFIDENCE_THRESHOLD:
                add_active_signal(result)
                logger.info(f"★★★ نیا سگنل ملا: {result['symbol']} - {result['signal']} @ {result['price']} ★★★")
                
                # --- اہم تبدیلی: اب ہم دونوں جگہ اطلاع بھیجیں گے ---
                # 1. ٹیلیگرام پر اطلاع بھیجیں
                await send_telegram_alert(result)
                
                # 2. تمام WebSocket کلائنٹس کو اطلاع بھیجیں
                await manager.broadcast({
                    "type": "new_signal",
                    "data": result
                })

    except Exception as e:
        logger.error(f"سگنل کی تلاش کے کام میں مہلک خرابی: {e}", exc_info=True)
    finally:
        db.close()
        logger.info(">>> سگنل کی تلاش کا کام (Hunt Job) مکمل ہوا۔")
        logger.info("=============================================")
        
