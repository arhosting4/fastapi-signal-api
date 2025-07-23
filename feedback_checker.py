# filename: feedback_checker.py

import httpx
import asyncio
import logging
from datetime import datetime, timedelta

from signal_tracker import get_all_signals, remove_active_signal
from utils import get_current_price_twelve_data
from database_crud import add_completed_trade, add_feedback_entry
from src.database.models import SessionLocal

# Configuration
EXPIRY_MINUTES = 15

# Logger setup
logger = logging.getLogger(__name__)

async def check_active_signals_job():
    """
    This job checks all active signals and evaluates their result (TP/SL/Expired).
    It runs every minute via APScheduler.
    """
    logger.info(f"[{datetime.utcnow()}] Running Feedback Checker Job...")

    active_signals = get_all_signals()
    if not active_signals:
        logger.info("No active signals to evaluate.")
        return

    db = SessionLocal()
    try:
        async with httpx.AsyncClient() as client:
            for signal in active_signals:
                try:
                    signal_id = signal.get("signal_id")
                    symbol = signal.get("symbol")
                    signal_type = signal.get("signal")
                    tp = signal.get("tp")
                    sl = signal.get("sl")
                    signal_time_str = signal.get("timestamp")

                    if not all([signal_id, symbol, signal_type, tp, sl, signal_time_str]):
                        logger.warning(f"Incomplete signal data: {signal}")
                        continue

                    signal_time = datetime.fromisoformat(signal_time_str)
                    current_price = await get_current_price_twelve_data(symbol, client)
                    if current_price is None:
                        logger.warning(f"Price fetch failed for {symbol}")
                        continue

                    outcome = None
                    feedback = None

                    if signal_type == "buy":
                        if current_price >= tp:
                            outcome = "tp_hit"
                            feedback = "correct"
                        elif current_price <= sl:
                            outcome = "sl_hit"
                            feedback = "incorrect"
                    elif signal_type == "sell":
                        if current_price <= tp:
                            outcome = "tp_hit"
                            feedback = "correct"
                        elif current_price >= sl:
                            outcome = "sl_hit"
                            feedback = "incorrect"

                    # Expiry check
                    if outcome is None and datetime.utcnow() - signal_time >= timedelta(minutes=EXPIRY_MINUTES):
                        outcome = "expired"
                        feedback = "incorrect"

                    # If outcome determined, record and remove
                    if outcome:
                        add_completed_trade(db, signal, outcome)
                        add_feedback_entry(db, symbol, signal.get("timeframe", "15m"), feedback)
                        remove_active_signal(signal_id)
                        logger.info(f"Signal {signal_id} marked as {outcome}")

                except Exception as e:
                    logger.error(f"Error processing signal {signal.get('signal_id')}: {e}")
    finally:
        db.close()
