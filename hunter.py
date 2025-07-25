# filename: hunter.py

import asyncio
import logging
import os
from sqlalchemy.orm import Session

from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import check_m15_opportunity, generate_final_signal
from signal_tracker import add_active_signal, get_active_signals_count
from messenger import send_telegram_alert
from models import SessionLocal
from websocket_manager import manager

logger = logging.getLogger(__name__)
LOCK_FILE_PATH = "/tmp/hunt_job.lock"
MAX_ACTIVE_SIGNALS = 5
FINAL_CONFIDENCE_THRESHOLD = 70.0

async def hunt_for_signals_job():
    # ★★★ فائل-بیسڈ لاکنگ میکانزم ★★★
    try:
        fd = os.open(LOCK_FILE_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        logger.warning("ہنٹ جاب پہلے ہی چل رہی ہے۔ اس نئے عمل کو روکا جا رہا ہے۔")
        return
    
    db = SessionLocal()
    try:
        if get_active_signals_count() >= MAX_ACTIVE_SIGNALS: return
        pairs = get_available_pairs()
        
        m15_fetch_tasks = [fetch_twelve_data_ohlc(pair, "15min") for pair in pairs]
        m15_results = await asyncio.gather(*m15_fetch_tasks)

        for i, m15_candles in enumerate(m15_results):
            if get_active_signals_count() >= MAX_ACTIVE_SIGNALS: break
            symbol = pairs[i]
            if not m15_candles or len(m15_candles) < 34: continue
            
            trend = check_m15_opportunity(symbol, m15_candles)
            if trend:
                m5_candles = await fetch_twelve_data_ohlc(symbol, "5min")
                if not m5_candles or len(m5_candles) < 34: continue
                
                signal_result = await generate_final_signal(db, symbol, trend, m5_candles)
                if signal_result and signal_result.get("status") == "ok" and signal_result.get("confidence", 0) >= FINAL_CONFIDENCE_THRESHOLD:
                    add_active_signal(signal_result)
                    await send_telegram_alert(signal_result)
                    await manager.broadcast({"type": "new_signal", "data": signal_result})
    finally:
        os.close(fd)
        os.remove(LOCK_FILE_PATH)
        if db.is_active: db.close()
            
