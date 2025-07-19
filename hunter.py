import asyncio
from datetime import datetime

from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import generate_final_signal
from signal_tracker import set_live_signal
from messenger import format_signal_message, send_telegram_message

MIN_CONFIDENCE_FOR_ALERT = 75.0

async def hunt_for_signals_job():
    print(f"[{datetime.now()}] --- AI Hunter: Starting a new hunt... ---")
    pairs_to_scan = get_available_pairs()
    timeframes = ["15m", "5m", "1m"]
    best_signal_so_far = {"confidence": 0.0}
    for symbol in pairs_to_scan:
        for tf in timeframes:
            print(f"HUNTING on: {symbol} - {tf}")
            try:
                candles = await fetch_twelve_data_ohlc(symbol, tf)
                if not candles or len(candles) < 50:
                    print(f"Skipping {symbol} - {tf} due to insufficient data.")
                    continue
                signal_result = await generate_final_signal(symbol, candles, tf, should_save_active=False)
                if signal_result and signal_result.get("signal") in ["buy", "sell"]:
                    current_confidence = signal_result.get("confidence", 0.0)
                    if current_confidence > best_signal_so_far.get("confidence", 0.0):
                        print(f"NEW BEST SIGNAL FOUND: {symbol} ({tf}) with {current_confidence:.2f}% confidence.")
                        best_signal_so_far = signal_result
                await asyncio.sleep(2)
            except Exception as e:
                print(f"ERROR during hunt for {symbol} on {tf}: {e}")
                continue
    if best_signal_so_far.get("confidence", 0.0) > 0:
        print(f"--- HUNT COMPLETE ---")
        print(f"Best signal: {best_signal_so_far.get('symbol')} ({best_signal_so_far.get('timeframe')})")
        print(f"Confidence: {best_signal_so_far.get('confidence'):.2f}%")
        set_live_signal(best_signal_so_far)
        if best_signal_so_far.get("confidence", 0.0) >= MIN_CONFIDENCE_FOR_ALERT:
            print(f"Confidence above {MIN_CONFIDENCE_FOR_ALERT}%. Sending Telegram alert...")
            try:
                telegram_message = format_signal_message(best_signal_so_far)
                await send_telegram_message(telegram_message)
            except Exception as e:
                print(f"ERROR sending Telegram message: {e}")
        else:
            print(f"Confidence below {MIN_CONFIDENCE_FOR_ALERT}%. No Telegram alert.")
    else:
        print("--- HUNT COMPLETE: No suitable signals found. ---")
        set_live_signal({"signal": "wait", "reason": "AI Hunter found no high-probability signals."})
        
