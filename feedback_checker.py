# filename: feedback_checker.py

import httpx
import asyncio
import logging
from datetime import datetime, timedelta

from utils import get_batch_prices_twelve_data
from signal_tracker import get_all_signals, remove_active_signal
from database_crud import add_completed_trade, add_feedback_entry
from models import SessionLocal
from websocket_manager import manager

logger = logging.getLogger(__name__)
EXPIRY_MINUTES = 15

async def check_active_signals_job():
    active_signals = get_all_signals()
    if not active_signals: return

    symbols_to_check = list(set([s['symbol'] for s in active_signals]))
    db = SessionLocal()
    try:
        async with httpx.AsyncClient() as client:
            # ★★★ مرکزی تبدیلی: ایک ہی API کال میں تمام قیمتیں حاصل کریں ★★★
            current_prices = await get_batch_prices_twelve_data(symbols_to_check, client)
            if current_prices is None: return

            for signal in active_signals:
                symbol = signal.get("symbol")
                if symbol in current_prices:
                    await process_single_signal(db, signal, current_prices[symbol])
    finally:
        if db.is_active: db.close()

async def process_single_signal(db, signal, current_price):
    try:
        signal_id, signal_type, tp, sl = signal.get("signal_id"), signal.get("signal"), signal.get("tp"), signal.get("sl")
        signal_time = datetime.fromisoformat(signal.get("timestamp"))
        outcome, feedback = None, None

        if signal_type == "buy" and current_price >= tp: outcome, feedback = "tp_hit", "correct"
        elif signal_type == "buy" and current_price <= sl: outcome, feedback = "sl_hit", "incorrect"
        elif signal_type == "sell" and current_price <= tp: outcome, feedback = "tp_hit", "correct"
        elif signal_type == "sell" and current_price >= sl: outcome, feedback = "sl_hit", "incorrect"
        
        if not outcome and (datetime.utcnow() - signal_time) >= timedelta(minutes=EXPIRY_MINUTES):
            outcome, feedback = "expired", "incorrect"

        if outcome:
            add_completed_trade(db, signal, outcome)
            add_feedback_entry(db, signal.get("symbol"), "M5/M15", feedback)
            remove_active_signal(signal_id)
            await manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal_id}})
    except Exception:
        pass
        
