# filename: feedback_checker.py

import httpx
import asyncio
import logging
from datetime import datetime, timedelta

from signal_tracker import get_all_signals, remove_active_signal
from utils import get_current_price_twelve_data
from database_crud import add_completed_trade, add_feedback_entry
from models import SessionLocal
from websocket_manager import manager

logger = logging.getLogger(__name__)

EXPIRY_MINUTES = 15

async def check_active_signals_job():
    """
    یہ جاب ہر منٹ چلتی ہے لیکن API کالز صرف ان منٹوں میں کرتی ہے
    جب ہنٹر جاب نہیں چل رہی ہوتی۔
    """
    now = datetime.utcnow()
    
    # ★★★ مرکزی اور حتمی منطق ★★★
    # اگر منٹ 5 سے تقسیم ہو سکتا ہے (0, 5, 10, ...)، تو ہنٹر جاب چلنے والی ہے۔
    # اس لیے، API کالز سے بچنے کے لیے اس عمل کو روک دیں۔
    if now.minute % 5 == 0:
        logger.info(f"ہنٹر جاب کا وقت (منٹ: {now.minute})۔ API کالز سے بچنے کے لیے فیڈ بیک چیکر کو روکا جا رہا ہے۔")
        return

    active_signals = get_all_signals()
    if not active_signals:
        return

    logger.info(f"فیڈ بیک چیکر: {len(active_signals)} فعال سگنلز کی نگرانی کی جا رہی ہے...")
    db = SessionLocal()
    try:
        async with httpx.AsyncClient() as client:
            tasks = [process_single_signal(db, signal, client) for signal in active_signals]
            await asyncio.gather(*tasks)
    finally:
        if db.is_active:
            db.close()

async def process_single_signal(db, signal, client):
    """ایک انفرادی سگنل پر کارروائی کرتا ہے۔"""
    try:
        signal_id = signal.get("signal_id")
        symbol = signal.get("symbol")
        signal_type = signal.get("signal")
        tp = signal.get("tp")
        sl = signal.get("sl")
        signal_time_str = signal.get("timestamp")

        if not all([signal_id, symbol, signal_type, tp, sl, signal_time_str]):
            return

        current_price = await get_current_price_twelve_data(symbol, client)
        if current_price is None:
            return

        outcome = None
        feedback = None
        signal_time = datetime.fromisoformat(signal_time_str)

        if signal_type == "buy":
            if current_price >= tp: outcome, feedback = "tp_hit", "correct"
            elif current_price <= sl: outcome, feedback = "sl_hit", "incorrect"
        elif signal_type == "sell":
            if current_price <= tp: outcome, feedback = "tp_hit", "correct"
            elif current_price >= sl: outcome, feedback = "sl_hit", "incorrect"

        if outcome is None and datetime.utcnow() - signal_time >= timedelta(minutes=EXPIRY_MINUTES):
            outcome, feedback = "expired", "incorrect"

        if outcome:
            logger.info(f"سگنل [{signal_id}] کا نتیجہ '{outcome}' ہے۔ اسے بند کیا جا رہا ہے۔")
            add_completed_trade(db, signal, outcome)
            add_feedback_entry(db, symbol, signal.get("timeframe", "M5/M15"), feedback)
            remove_active_signal(signal_id)
            await manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal_id}})

    except Exception as e:
        logger.error(f"سگنل [{signal.get('signal_id')}] پر کارروائی کے دوران خرابی: {e}", exc_info=True)

