import asyncio
import random
from datetime import datetime

# ہمارے پروجیکٹ کے ایجنٹس
from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import generate_final_signal
from signal_tracker import set_live_signal, get_live_signal
# --- نیا: میسنجر ایجنٹ کو امپورٹ کریں ---
from messenger import format_signal_message, send_telegram_message

# سگنل بھیجنے کے لیے کم از کم اعتماد کی حد
MIN_CONFIDENCE_FOR_ALERT = 75.0

async def hunt_for_signals_job():
    """
    یہ مرکزی ہنٹر جاب ہے جو مارکیٹوں کو اسکین کرتی ہے اور بہترین سگنل تلاش کرتی ہے۔
    اب یہ ٹیلیگرام الرٹس بھی بھیجتی ہے۔
    """
    print(f"[{datetime.now()}] --- AI Hunter: Starting a new hunt... ---")
    
    pairs_to_scan = get_available_pairs()
    timeframes = ["15m", "5m", "1m"] # ترجیح: بڑے ٹائم فریم سے چھوٹے کی طرف
    
    best_signal_so_far = {"confidence": 0.0}

    for symbol in pairs_to_scan:
        for tf in timeframes:
            print(f"HUNTING on: {symbol} - {tf}")
            candles = await fetch_twelve_data_ohlc(symbol, tf)
            
            if not candles or len(candles) < 50:
                print(f"Skipping {symbol} - {tf} due to insufficient data.")
                continue

            # AI انجن سے تجزیہ حاصل کریں
            # اہم: ہم یہاں should_save_active=False بھیج رہے ہیں تاکہ سگنل فوری طور پر محفوظ نہ ہو
            signal_result = await generate_final_signal(symbol, candles, tf, should_save_active=False)

            if signal_result and signal_result.get("signal") in ["buy", "sell"]:
                current_confidence = signal_result.get("confidence", 0.0)
                
                # اگر یہ اب تک کا بہترین سگنل ہے، تو اسے محفوظ کر لیں
                if current_confidence > best_signal_so_far.get("confidence", 0.0):
                    print(f"NEW BEST SIGNAL FOUND: {symbol} ({tf}) with {current_confidence:.2f}% confidence.")
                    best_signal_so_far = signal_result
            
            # API کی حد سے بچنے کے لیے تھوڑا وقفہ
            await asyncio.sleep(2) 

    # تمام جوڑوں اور ٹائم فریمز کو اسکین کرنے کے بعد، حتمی فیصلہ کریں
    if best_signal_so_far.get("confidence", 0.0) > 0:
        print(f"--- HUNT COMPLETE ---")
        print(f"Best signal found: {best_signal_so_far.get('symbol')} ({best_signal_so_far.get('timeframe')})")
        print(f"Confidence: {best_signal_so_far.get('confidence'):.2f}%")
        
        # لائیو سگنل کو سیٹ کریں تاکہ ویب سائٹ پر نظر آئے
        set_live_signal(best_signal_so_far)

        # --- اہم تبدیلی: ٹیلیگرام الرٹ بھیجنے کی منطق ---
        # اگر اعتماد کی سطح ہماری مقررہ حد سے زیادہ ہے، تو ٹیلیگرام پر پیغام بھیجیں
        if best_signal_so_far.get("confidence", 0.0) >= MIN_CONFIDENCE_FOR_ALERT:
            print(f"Confidence is above threshold ({MIN_CONFIDENCE_FOR_ALERT}%)! Sending Telegram alert...")
            # پیغام کو فارمیٹ کریں
            telegram_message = format_signal_message(best_signal_so_far)
            # پیغام بھیجیں
            await send_telegram_message(telegram_message)
        else:
            print(f"Confidence is below threshold ({MIN_CONFIDENCE_FOR_ALERT}%). No Telegram alert sent.")

    else:
        print("--- HUNT COMPLETE: No suitable trading signals found in this cycle. ---")
        # اگر کوئی سگنل نہیں ملا، تو ویب سائٹ پر "WAIT" دکھائیں
        set_live_signal({
            "signal": "wait",
            "reason": "AI Hunter did not find any high-probability signals in the last scan."
        })

