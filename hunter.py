import asyncio
from datetime import datetime
from typing import List, Dict, Any

# ہمارے پروجیکٹ کے ماڈیولز
from utils import fetch_twelve_data_ohlc
from fusion_engine import generate_final_signal
from signal_tracker import save_live_signal

# --- جوڑوں کی فہرستوں کی نئی تعریف ---
FOREX_PAIRS = ["XAU/USD", "EUR/USD", "GBP/USD"]
CRYPTO_PAIRS = ["BTC/USD"]
ALL_PAIRS = FOREX_PAIRS + CRYPTO_PAIRS

TIMEFRAMES_TO_SCAN = ["1m", "5m", "15m"]

def get_active_pairs() -> List[str]:
    """
    موجودہ دن کی بنیاد پر فعال جوڑوں کی فہرست واپس کرتا ہے۔
    UTC ٹائم زون کا استعمال کرتا ہے جو سرورز کے لیے معیاری ہے۔
    """
    # datetime.utcnow().weekday() پیر کو 0 اور اتوار کو 6 واپس کرتا ہے۔
    # فاریکس مارکیٹ جمعہ کی رات (UTC) بند ہوتی ہے اور اتوار کی رات (UTC) کھلتی ہے۔
    # ہم ہفتہ (5) اور اتوار (6) کے زیادہ تر حصے میں صرف کرپٹو کو دیکھیں گے۔
    current_day_utc = datetime.utcnow().weekday()
    
    # ہفتہ (5) اور اتوار (6)
    if current_day_utc == 5 or current_day_utc == 6:
        print("WEEKEND MODE: Scanning CRYPTO pairs only.")
        return CRYPTO_PAIRS
    else:
        print("WEEKDAY MODE: Scanning ALL pairs (Forex + Crypto).")
        return ALL_PAIRS

async def hunt_for_signals_job():
    """
    یہ مرکزی پس منظر کی جاب ہے جو اب مارکیٹ کے اوقات سے آگاہ ہے۔
    """
    print(f"\n--- HUNTER JOB: Starting new hunt at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} ---")
    
    # --- اہم تبدیلی: فعال جوڑوں کی فہرست حاصل کریں ---
    active_pairs_to_scan = get_active_pairs()
    
    all_possible_signals: List[Dict[str, Any]] = []

    for pair in active_pairs_to_scan:
        for tf in TIMEFRAMES_TO_SCAN:
            print(f"HUNTING on: {pair} - {tf}")
            
            candles = await fetch_twelve_data_ohlc(pair, tf)
            
            if not candles or len(candles) < 50:
                print(f"Skipping {pair} - {tf} due to insufficient data.")
                continue
            
            potential_signal = await generate_final_signal(pair, candles, tf, should_save_active=False)
            
            if potential_signal and potential_signal.get("signal") in ["buy", "sell"]:
                all_possible_signals.append(potential_signal)

    best_signal = None
    if not all_possible_signals:
        print("--- HUNTER JOB: No quality signals found in this cycle. ---")
        best_signal = {
            "symbol": "N/A",
            "signal": "wait",
            "reason": "AI is actively scanning the markets for the next high-quality opportunity.",
            "timestamp": asyncio.get_event_loop().time()
        }
    else:
        all_possible_signals.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        best_signal = all_possible_signals[0]
        print(f"--- HUNTER JOB: Best signal found! {best_signal.get('symbol')} ({best_signal.get('timeframe')}) with {best_signal.get('confidence')}% confidence. ---")

    save_live_signal(best_signal)
    
