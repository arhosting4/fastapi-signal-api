# filename: hunter.py

import asyncio
import logging
from sqlalchemy.orm import Session

from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import generate_final_signal
from signal_tracker import add_active_signal, get_active_signals_count
from messenger import send_telegram_alert
from models import SessionLocal
from websocket_manager import manager

logger = logging.getLogger(__name__)

MAX_ACTIVE_SIGNALS = 5
FINAL_CONFIDENCE_THRESHOLD = 60.0

async def hunt_for_signals_job():
    """
    سگنل کی تلاش کا سادہ کام جو صرف 15 منٹ کے ٹائم فریم پر چلتا ہے۔
    """
    logger.info(">>> سگنل کی تلاش کا سادہ کام شروع ہو رہا ہے...")
    if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
        logger.info("فعال سگنلز کی زیادہ سے زیادہ حد تک پہنچ گئے ہیں۔")
        return

    pairs = get_available_pairs()
    db = SessionLocal()
    try:
        for pair in pairs:
            if get_active_signals_count() >= MAX_ACTIVE_SIGNALS: break
            
            # صرف 15 منٹ کا ڈیٹا حاصل کریں
            candles = await fetch_twelve_data_ohlc(pair, "15min")
            if not candles or len(candles) < 34:
                logger.warning(f"[{pair}] کے لیے ناکافی کینڈل ڈیٹا۔")
                continue

            signal_result = await generate_final_signal(db, pair, candles)
            
            if signal_result and signal_result.get("status") == "ok" and signal_result.get("confidence", 0) >= FINAL_CONFIDENCE_THRESHOLD:
                add_active_signal(signal_result)
                logger.info(f"★★★ نیا سگنل ملا: {signal_result} ★★★")
                await send_telegram_alert(signal_result)
                await manager.broadcast({"type": "new_signal", "data": signal_result})
    finally:
        db.close()
        logger.info(">>> سگنل کی تلاش کا کام مکمل ہوا۔")
        
