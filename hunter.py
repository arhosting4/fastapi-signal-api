# filename: hunter.py

import asyncio
from sqlalchemy.orm import Session
from datetime import datetime

# مقامی امپورٹس
from utils import get_available_pairs, fetch_twelve_data_ohlc
from fusion_engine import generate_final_signal
from signal_tracker import set_active_signals
from messenger import send_telegram_message
import database_crud as crud

# سگنل کے لیے کم از کم خود اعتمادی کی حد
MIN_CONFIDENCE_THRESHOLD = 65.0

async def hunt_for_signals_job(db_session_factory):
    """
    تمام دستیاب جوڑوں اور ٹائم فریمز پر سگنل تلاش کرتا ہے
    اور تمام اہل سگنلز کو آگے بھیجتا ہے۔
    """
    print(f"\n--- HUNTER (Multi-Signal Mode): Waking up at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    db: Session = db_session_factory()
    try:
        pairs_to_check = get_available_pairs()
        timeframes = ["1m", "5m", "15m"]
        all_qualified_signals = []

        # تمام جوڑوں اور ٹائم فریمز پر سگنل تلاش کریں
        for pair in pairs_to_check:
            for tf in timeframes:
                print(f"--- HUNTING on: {pair} - {tf} ---")
                candles = await fetch_twelve_data_ohlc(pair, tf, 100)
                if not candles or len(candles) < 34:
                    print(f"Skipping {pair} - {tf} due to insufficient data.")
                    continue
                
                # AI انجن سے حتمی سگنل حاصل کریں
                signal_result = await generate_final_signal(db, pair, candles, tf)
                
                # چیک کریں کہ کیا سگنل ہمارے معیار پر پورا اترتا ہے
                if signal_result and signal_result.get("status") == "ok" and signal_result.get("confidence", 0) >= MIN_CONFIDENCE_THRESHOLD:
                    all_qualified_signals.append(signal_result)
                    print(f"✅ Found a QUALIFIED signal for {pair} - {tf} with confidence {signal_result.get('confidence')}%")

        # --- اہم ترین تبدیلی: اب ہم تمام اہل سگنلز پر کارروائی کریں گے ---
        if all_qualified_signals:
            print(f"--- HUNTER: Found {len(all_qualified_signals)} qualified signals. Processing all of them. ---")
            
            # 1. تمام سگنلز کو فرنٹ اینڈ کے لیے JSON فائل میں محفوظ کریں
            set_active_signals(all_qualified_signals)
            
            # 2. ہر سگنل کے لیے، اسے ڈیٹا بیس میں شامل کریں اور ٹیلیگرام پر بھیجیں
            for signal in all_qualified_signals:
                # add_active_trade_to_db فنکشن خود چیک کرے گا کہ آیا اسی جوڑے کا پرانا سگنل تبدیل کرنا ہے یا نیا شامل کرنا ہے
                is_new_or_flipped = crud.add_active_trade_to_db(db, signal)
                
                # صرف نئے یا تبدیل شدہ سگنلز کے لیے الرٹ بھیجیں تاکہ بار بار پیغامات نہ آئیں
                if is_new_or_flipped:
                    await send_telegram_message(signal)
        else:
            # اگر کوئی اہل سگنل نہیں ملتا ہے، تو فرنٹ اینڈ کو صاف کریں
            print("--- HUNTER: No qualified signals found in this cycle. Clearing active signals display. ---")
            set_active_signals([])

    except Exception as e:
        print(f"--- CRITICAL ERROR in hunt_for_signals_job: {e} ---")
    finally:
        db.close()
        print(f"--- HUNTER: Cycle finished. Sleeping... ---")

