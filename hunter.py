# hunter.py

import asyncio
from datetime import datetime
from typing import List, Dict, Any

from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import generate_final_signal
from signal_tracker import set_live_signal, add_active_signal, get_active_signals_count
from messenger import send_telegram_alert

# --- نئی تبدیلی: ڈیٹا بیس سیشن کے لیے ---
from src.database.models import SessionLocal

MAX_ACTIVE_SIGNALS = 5

async def hunt_for_signals_job():
    """
    مارکیٹ کو اسکین کرتا ہے، بہترین سگنل تلاش کرتا ہے، اور اسے لائیو کرتا ہے۔
    """
    print(f"--- [{datetime.now()}] Running Signal Hunter Job ---")
    
    if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
        print(f"--- Hunter paused: Maximum active signals ({MAX_ACTIVE_SIGNALS}) reached. ---")
        return

    available_pairs = get_available_pairs()
    best_signal = None
    highest_confidence = 55.0 # کم از کم اعتماد کی حد

    # --- نئی تبدیلی: ڈیٹا بیس سیشن بنائیں ---
    db = SessionLocal()
    try:
        for pair in available_pairs:
            # مختلف ٹائم فریمز کو چیک کریں
            for tf in ["1m", "5m", "15m"]:
                try:
                    candles = await fetch_twelve_data_ohlc(pair, tf, 100)
                    if not candles or len(candles) < 34:
                        continue
                    
                    # --- نئی تبدیلی: generate_final_signal کو ڈیٹا بیس سیشن فراہم کریں ---
                    signal_result = await generate_final_signal(db, pair, candles, tf)

                    if signal_result and signal_result.get("status") == "ok":
                        confidence = signal_result.get("confidence", 0)
                        if confidence > highest_confidence:
                            highest_confidence = confidence
                            best_signal = signal_result
                            print(f"--- New best signal found: {pair} ({tf}) with confidence {confidence:.2f}% ---")

                except Exception as e:
                    print(f"--- Hunter ERROR processing {pair} ({tf}): {e} ---")
                await asyncio.sleep(1) # API کی حد سے بچنے کے لیے
    finally:
        # --- نئی تبدیلی: ڈیٹا بیس سیشن کو بند کریں ---
        db.close()

    if best_signal:
        print(f"--- !!! FINAL BEST SIGNAL SELECTED: {best_signal['symbol']} ({best_signal['timeframe']}) at {highest_confidence:.2f}% confidence. Making it live. !!! ---")
        set_live_signal(best_signal)
        add_active_signal(best_signal)
        await send_telegram_alert(best_signal)
    else:
        print("--- No high-quality signal found in this hunt. ---")
        
