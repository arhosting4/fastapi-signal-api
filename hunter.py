# filename: hunter.py

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
from websocket_manager import manager

logger = logging.getLogger(__name__)

# کنفیگریشن
MAX_ACTIVE_SIGNALS = 5
FINAL_CONFIDENCE_THRESHOLD = 70.0 # حد کو تھوڑا بڑھا دیا گیا ہے

async def analyze_pair(db: Session, pair: str) -> Optional[Dict[str, Any]]:
    """
    ایک تجارتی جوڑے کا ملٹی ٹائم فریم تجزیہ کرتا ہے اور اگر کوئی سگنل ملے تو اسے واپس کرتا ہے۔
    """
    # 1. M15 ڈیٹا حاصل کریں
    logger.info(f"[{pair}] کے لیے M15 کینڈل ڈیٹا حاصل کیا جا رہا ہے...")
    m15_candles = await fetch_twelve_data_ohlc(pair, "15min")
    if not m15_candles or len(m15_candles) < 34: # Supertrend اور دیگر انڈیکیٹرز کے لیے کافی ڈیٹا
        logger.warning(f"[{pair}] کے لیے ناکافی M15 کینڈل ڈیٹا ({len(m15_candles) if m15_candles else 0})۔")
        return None

    # 2. M5 ڈیٹا حاصل کریں
    logger.info(f"[{pair}] کے لیے M5 کینڈل ڈیٹا حاصل کیا جا رہا ہے...")
    m5_candles = await fetch_twelve_data_ohlc(pair, "5min")
    if not m5_candles or len(m5_candles) < 34:
        logger.warning(f"[{pair}] کے لیے ناکافی M5 کینڈل ڈیٹا ({len(m5_candles) if m5_candles else 0})۔")
        return None

    # 3. AI فیوژن انجن کو دونوں ٹائم فریمز کا ڈیٹا بھیجیں
    logger.info(f"[{pair}] کے لیے AI فیوژن انجن چلایا جا رہا ہے...")
    signal_result = await generate_final_signal(db, pair, m15_candles, m5_candles)
    
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
    logger.info(">>> سگنل کی تلاش کا کام (Hunt Job) v2.0 شروع ہو رہا ہے...")
    logger.info("=============================================")

    if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
        logger.info("فعال سگنلز کی زیادہ سے زیادہ حد تک پہنچ گئے ہیں۔ شکار روکا جا رہا ہے۔")
        return

    pairs = get_available_pairs()
    logger.info(f"تجزیہ کے لیے دستیاب جوڑے: {pairs}")
    db = SessionLocal()
    
    try:
        # تمام جوڑوں کا تجزیہ متوازی طور پر کریں
        tasks = [analyze_pair(db, pair) for pair in pairs]
        results = await asyncio.gather(*tasks)

        for result in results:
            if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
                logger.info("سگنل کی حد تک پہنچ گئے۔ شکار روکا جا رہا ہے۔")
                break

            if result and result.get("confidence", 0) >= FINAL_CONFIDENCE_THRESHOLD:
                add_active_signal(result)
                logger.info(f"★★★ نیا سگنل ملا: {result['symbol']} - {result['signal']} @ {result['price']} ★★★")
                
                # ٹیلیگرام اور WebSocket پر اطلاع بھیجیں
                await send_telegram_alert(result)
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
        
