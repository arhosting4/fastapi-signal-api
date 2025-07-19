# hunter.py

import asyncio
from sqlalchemy.orm import Session
from datetime import datetime

from utils import get_available_pairs, fetch_twelve_data_ohlc
from fusion_engine import generate_final_signal
# --- اہم تبدیلی: signal_tracker سے نئے فنکشنز امپورٹ کریں ---
from signal_tracker import set_active_signals
from messenger import send_telegram_message
import database_crud as crud

MIN_CONFIDENCE_THRESHOLD = 65.0 # کم از کم اعتماد کا معیار

async def hunt_for_signals_job(db_session_factory):
    """
    تمام دستیاب جوڑوں اور ٹائم فریمز پر اعلیٰ معیار کے سگنلز کی تلاش کرتا ہے۔
    """
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
                
                # --- اہم منطق: صرف اہل سگنلز کو شامل کریں ---
                if signal_result and signal_result.get("status") == "ok" and signal_result.get("confidence", 0) >= MIN_CONFIDENCE_THRESHOLD:
                    # ٹیلیگرام پیغام بھیجنے سے پہلے سگنل میں کینڈلز شامل کریں
                    signal_result_with_candles = signal_result.copy()
                    signal_result_with_candles['candles'] = candles
                    all_potential_signals.append(signal_result_with_candles)
                    print(f"✅ Found a QUALIFIED signal for {pair} - {tf} with confidence {signal_result.get('confidence')}%")

        # --- اہم تبدیلی: تمام اہل سگنلز کو محفوظ کریں ---
        if all_potential_signals:
            # ٹیلیگرام بھیجنے سے پہلے کینڈلز کو ہٹا دیں تاکہ فائل چھوٹی رہے
            signals_to_save = [s.copy() for s in all_potential_signals]
            for s in signals_to_save:
                s.pop('candles', None)
            
            set_active_signals(signals_to_save)
            
            # --- ٹیلیگرام الرٹ کی منطق (ابھی بھی صرف بہترین سگنل کے لیے) ---
            # مستقبل میں ہم اسے بھی اپ گریڈ کر سکتے ہیں
            best_signal = max(all_potential_signals, key=lambda x: x.get('confidence', 0))
            
            # چیک کریں کہ کیا یہ سگنل پہلے ہی بھیجا جا چکا ہے
            is_new_trade = crud.add_active_trade_to_db(db, best_signal)
            if is_new_trade:
                await send_telegram_message(best_signal)
        else:
            # اگر کوئی اہل سگنل نہیں ملتا تو فائل کو صاف کر دیں
            print("--- HUNTER: No qualified signals found in this cycle. Clearing active signals. ---")
            set_active_signals([])

    except Exception as e:
        print(f"--- CRITICAL ERROR in hunt_for_signals_job: {e} ---")
    finally:
        db.close()
        print(f"--- HUNTER: Cycle finished. Sleeping... ---")
        
