# filename: feedback_checker.py

import httpx
import asyncio
from datetime import datetime, timedelta

# --- اہم اور فوری اصلاح: get_all_signals کا نام get_all_active_signals میں تبدیل کیا گیا ---
from signal_tracker import get_all_active_signals, remove_active_signal
from utils import get_current_price_twelve_data
from database_crud import add_completed_trade, add_feedback_entry
from src.database.models import SessionLocal

async def check_active_signals_job():
    print(f"--- [{datetime.now()}] Running Feedback Checker Job ---")
    # --- تبدیلی: درست فنکشن نام کا استعمال ---
    active_signals = get_all_active_signals()
    if not active_signals:
        return

    db = SessionLocal()
    try:
        async with httpx.AsyncClient() as client:
            for signal in active_signals:
                # یقینی بنائیں کہ سگنل میں تمام ضروری کلیدیں موجود ہیں
                signal_id = signal.get("signal_id")
                symbol = signal.get("symbol")
                signal_type = signal.get("signal")
                tp = signal.get("tp")
                sl = signal.get("sl")
                signal_time_str = signal.get("timestamp")

                if not all([signal_id, symbol, signal_type, tp, sl, signal_time_str]):
                    print(f"--- Feedback Checker WARNING: Skipping incomplete signal data: {signal} ---")
                    continue

                current_price = await get_current_price_twelve_data(symbol, client)
                if current_price is None:
                    continue

                outcome, feedback = (None, None)
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
                
                # سگنل کی میعاد ختم ہونے کی جانچ
                if outcome is None:
                    try:
                        signal_time = datetime.fromisoformat(signal_time_str)
                        if (datetime.utcnow() - signal_time) > timedelta(hours=24):
                            outcome, feedback = "expired", "missed"
                    except ValueError:
                        # اگر ٹائم اسٹیمپ غلط فارمیٹ میں ہے تو اسے نظر انداز کریں
                        pass
                
                if outcome and feedback:
                    print(f"--- Signal {signal_id} for {symbol} outcome: {outcome}. Saving to DB... ---")
                    add_completed_trade(db, signal, outcome)
                    add_feedback_entry(db, symbol, signal.get('timeframe', 'N/A'), feedback)
                    remove_active_signal(signal_id)
                    await asyncio.sleep(0.5) # API اور DB پر بوجھ کم کرنے کے لیے
    finally:
        db.close()
        
