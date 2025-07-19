import httpx
import asyncio
from datetime import datetime, timedelta

from signal_tracker import get_all_signals, remove_active_signal
from utils import get_current_price_twelve_data
from database_crud import add_completed_trade, add_feedback_entry
from src.database.models import SessionLocal

async def check_active_signals_job():
    print(f"--- [{datetime.now()}] Running Feedback Checker Job ---")
    active_signals = get_all_signals()
    if not active_signals:
        print("--- No active signals to check. ---")
        return

    db = SessionLocal()
    try:
        async with httpx.AsyncClient() as client:
            for signal in active_signals:
                signal_id, symbol, signal_type, tp, sl, signal_time_str = (
                    signal.get("signal_id"), signal.get("symbol"), signal.get("signal"),
                    signal.get("tp"), signal.get("sl"), signal.get("timestamp")
                )
                if not all([signal_id, symbol, signal_type, tp, sl, signal_time_str]): continue

                current_price = await get_current_price_twelve_data(symbol, client)
                if current_price is None: continue

                outcome, feedback = (None, None)
                if signal_type == "buy":
                    if current_price >= tp: outcome, feedback = "tp_hit", "correct"
                    elif current_price <= sl: outcome, feedback = "sl_hit", "incorrect"
                elif signal_type == "sell":
                    if current_price <= tp: outcome, feedback = "tp_hit", "correct"
                    elif current_price >= sl: outcome, feedback = "sl_hit", "incorrect"
                
                if outcome is None and (datetime.utcnow() - datetime.fromisoformat(signal_time_str)) > timedelta(hours=24):
                    outcome, feedback = "expired", "missed"
                
                if outcome and feedback:
                    print(f"--- Signal {signal_id} outcome: {outcome}. Saving to DB... ---")
                    add_completed_trade(db, signal, outcome)
                    add_feedback_entry(db, symbol, signal.get('timeframe', 'N/A'), feedback)
                    remove_active_signal(signal_id)
    finally:
        db.close()
    print(f"--- [{datetime.now()}] Feedback Checker Job Finished ---")
    
