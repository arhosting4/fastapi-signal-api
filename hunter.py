# filename: hunter.py
import asyncio
from sqlalchemy.orm import Session
from datetime import datetime

from utils import get_available_pairs, fetch_twelve_data_ohlc
from fusion_engine import generate_final_signal
from signal_tracker import set_active_signals
from messenger import send_telegram_message
import database_crud as crud

MIN_CONFIDENCE_THRESHOLD = 65.0

async def hunt_for_signals_job(db_session_factory):
    print(f"\n--- HUNTER: Waking up at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    db: Session = db_session_factory()
    try:
        pairs_to_check = get_available_pairs()
        timeframes = ["1m", "5m", "15m"]
        all_potential_signals = []

        for pair in pairs_to_check:
            for tf in timeframes:
                print(f"--- HUNTING on: {pair} - {tf} ---")
                candles = await fetch_twelve_data_ohlc(pair, tf, 100)
                if not candles or len(candles) < 34:
                    print(f"Skipping {pair} - {tf} due to insufficient data.")
                    continue
                
                signal_result = await generate_final_signal(db, pair, candles, tf)
                
                if signal_result and signal_result.get("status") == "ok" and signal_result.get("confidence", 0) >= MIN_CONFIDENCE_THRESHOLD:
                    all_potential_signals.append(signal_result)
                    print(f"✅ Found a QUALIFIED signal for {pair} - {tf} with confidence {signal_result.get('confidence')}%")

        if all_potential_signals:
            set_active_signals(all_potential_signals)
            
            best_signal = max(all_potential_signals, key=lambda x: x.get('confidence', 0))
            
            is_new_trade = crud.add_active_trade_to_db(db, best_signal)
            if is_new_trade:
                await send_telegram_message(best_signal)
        else:
            print("--- HUNTER: No qualified signals found. Clearing active signals. ---")
            set_active_signals([])

    except Exception as e:
        print(f"--- CRITICAL ERROR in hunt_for_signals_job: {e} ---")
    finally:
        db.close()
        print(f"--- HUNTER: Cycle finished. Sleeping... ---")
        
