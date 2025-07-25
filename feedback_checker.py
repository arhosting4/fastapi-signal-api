# filename: feedback_checker.py

import httpx
import asyncio
import logging
from datetime import datetime, timedelta

# utils سے نیا فنکشن امپورٹ کریں
from utils import get_batch_prices_twelve_data
from signal_tracker import get_all_signals, remove_active_signal
from database_crud import add_completed_trade, add_feedback_entry
from models import SessionLocal
from websocket_manager import manager

logger = logging.getLogger(__name__)

EXPIRY_MINUTES = 15

async def check_active_signals_job():
    """
    یہ جاب ایک ہی API کال میں تمام فعال سگنلز کی قیمتیں حاصل کرتی ہے۔
    """
    active_signals = get_all_signals()
    if not active_signals:
        return

    logger.info(f"فیڈ بیک چیکر: {len(active_signals)} فعال سگنلز کی نگرانی کی جا رہی ہے...")
    
    # تمام فعال سمبلز کی ایک منفرد فہرست بنائیں
    symbols_to_check = list(set([s['symbol'] for s in active_signals]))

    db = SessionLocal()
    try:
        async with httpx.AsyncClient() as client:
            # ★★★ مرکزی تبدیلی: ایک ہی API کال میں تمام قیمتیں حاصل کریں ★★★
            current_prices = await get_batch_prices_twelve_data(symbols_to_check, client)

            if current_prices is None:
                logger.warning("قیمتیں حاصل کرنے میں ناکامی، اس سائیکل کو چھوڑا جا رہا ہے۔")
                return

            for signal in active_signals:
                symbol = signal.get("symbol")
                # اگر اس سمبل کی قیمت ملی ہے تو ہی آگے بڑھیں
                if symbol in current_prices:
                    await process_single_signal(db, signal, current_prices[symbol])

    finally:
        if db.is_active:
            db.close()

async def process_single_signal(db, signal, current_price):
    """ایک انفرادی سگنل پر کارروائی کرتا ہے (اب اسے قیمت باہر سے ملتی ہے)۔"""
    try:
        signal_id = signal.get("signal_id")
        signal_type = signal.get("signal")
        tp = signal.get("tp")
        sl = signal.get("sl")
        signal_time = datetime.fromisoformat(signal.get("timestamp"))

        outcome, feedback = None, None

        if signal_type == "buy":
            if current_price >= tp: outcome, feedback = "tp_hit", "correct"
            elif current_price <= sl: outcome, feedback = "sl_hit", "incorrect"
        elif signal_type == "sell":
            if current_price <= tp: outcome, feedback = "tp_hit", "correct"
            elif current_price >= sl: outcome, feedback = "sl_hit", "incorrect"

        if not outcome and (datetime.utcnow() - signal_time) >= timedelta(minutes=EXPIRY_MINUTES):
            outcome, feedback = "expired", "incorrect"

        if outcome:
            logger.info(f"سگنل [{signal_id}] کا نتیجہ '{outcome}' ہے۔ اسے بند کیا جا رہا ہے۔")
            add_completed_trade(db, signal, outcome)
            add_feedback_entry(db, signal.get("symbol"), signal.get("timeframe", "M5/M15"), feedback)
            remove_active_signal(signal_id)
            await manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal_id}})

    except Exception as e:
        logger.error(f"سگنل [{signal.get('signal_id')}] پر کارروائی کے دوران خرابی: {e}", exc_info=True)
            
