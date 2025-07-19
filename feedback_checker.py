# feedback_checker.py

import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# ہمارے پروجیکٹ کے ماڈیولز
from signal_tracker import get_all_signals, remove_active_signal
from utils import get_current_price_twelve_data
    
# --- نئی تبدیلی: ڈیٹا بیس کے لیے امپورٹس ---
from database_crud import add_completed_trade, add_feedback_entry
from src.database.models import SessionLocal

async def check_active_signals_job():
    """
    تمام فعال سگنلز کو چیک کرتا ہے، ان کا نتیجہ متعین کرتا ہے، اور اسے ڈیٹا بیس میں محفوظ کرتا ہے۔
    """
    print(f"--- [{datetime.now()}] Running Feedback Checker Job ---")
    active_signals = get_all_signals()
    if not active_signals:
        print("--- No active signals to check. ---")
        return

    print(f"--- Found {len(active_signals)} active signals to check. ---")
        
    # --- نئی تبدیلی: ڈیٹا بیس سیشن بنائیں ---
    db = SessionLocal()
        
    try:
        async with httpx.AsyncClient() as client:
            for signal in active_signals:
                signal_id = signal.get("signal_id")
                symbol = signal.get("symbol")
                signal_type = signal.get("signal")
                tp = signal.get("tp")
                sl = signal.get("sl")
                signal_time_str = signal.get("timestamp")

                if not all([signal_id, symbol, signal_type, tp, sl, signal_time_str]):
                    continue

                current_price = await get_current_price_twelve_data(symbol, client)
                if current_price is None:
                    continue

                print(f"--- Checking {signal_id} for {symbol}. Price: {current_price}, TP: {tp}, SL: {sl} ---")
                    
                outcome, feedback = None, None
                    
                if signal_type == "buy":
                    if current_price >= tp:
                        outcome, feedback = "tp_hit", "correct"
                    elif current_price <= sl:
                        outcome, feedback = "sl_hit", "incorrect"
                elif signal_type == "sell":
                    if current_price <= tp:
                        outcome, feedback = "tp_hit", "correct"
                    elif current_price >= sl:
                        outcome, feedback = "sl_hit", "incorrect"
                    
                signal_time = datetime.fromisoformat(signal_time_str)
                if outcome is None and (datetime.utcnow() - signal_time) > timedelta(hours=24):
                    outcome, feedback = "expired", "missed"
                    
                if outcome and feedback:
                    print(f"--- Signal {signal_id} outcome: {outcome}. Saving to DB... ---")
                        
                    # --- نئی تبدیلی: JSON کی بجائے ڈیٹا بیس میں محفوظ کریں ---
                    add_completed_trade(db, signal, outcome)
                    add_feedback_entry(db, symbol, signal.get('timeframe', 'N/A'), feedback)
                        
                    # فعال سگنلز کی فہرست سے ہٹائیں
                    remove_active_signal(signal_id)
    finally:
        # --- نئی تبدیلی: ڈیٹا بیس سیشن کو بند کریں ---
        db.close()

    print(f"--- [{datetime.now()}] Feedback Checker Job Finished ---")

