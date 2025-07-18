import os
import httpx
import asyncio
from datetime import datetime

# ہمارے اپنے پروجیکٹ کی فائلیں
from signal_tracker import get_all_signals, update_signal_status
from feedback_memory import save_feedback

# Twelve Data API کلید
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

async def fetch_current_price_twelve_data(symbol: str, client: httpx.AsyncClient) -> float | None:
    """Twelve Data سے ایک علامت کے لیے تازہ ترین قیمت حاصل کرتا ہے۔"""
    if not TWELVE_DATA_API_KEY:
        return None
    
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_DATA_API_KEY}"
    try:
        response = await client.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        price = data.get("price")
        if price:
            return float(price)
        return None
    except Exception as e:
        print(f"Error fetching real-time price for {symbol}: {e}")
        return None

async def check_active_signals_job():
    """
    یہ پس منظر کی جاب فعال سگنلز کی نگرانی کرتی ہے۔
    """
    print(f"--- [{datetime.now()}] Running Background Signal Checker Job (using Twelve Data) ---")
    
    all_signals = get_all_signals()
    active_signals = [s for s in all_signals if s.get('status') == 'active']

    if not active_signals:
        print("No active signals to check.")
        return

    print(f"Found {len(active_signals)} active signals to check.")

    async with httpx.AsyncClient() as client:
        for signal in active_signals:
            signal_id = signal.get("id")
            symbol = signal.get("symbol")
            signal_type = signal.get("signal")
            tp = signal.get("tp")
            sl = signal.get("sl")
            timeframe = signal.get("timeframe")

            if not all([signal_id, symbol, signal_type, tp, sl, timeframe]):
                continue

            # --- اہم تبدیلی: yfinance کی جگہ نیا فنکشن ---
            current_price = await fetch_current_price_twelve_data(symbol, client)
            
            if current_price is None:
                print(f"Could not fetch real-time price for {symbol}. Skipping check.")
                continue
            
            print(f"Checking: {signal_id} | {symbol} | Price: {current_price:.5f} | TP: {tp:.5f} | SL: {sl:.5f}")

            new_status = None
            feedback = None

            if signal_type == "buy":
                if current_price >= tp:
                    new_status, feedback = "tp_hit", "correct"
                elif current_price <= sl:
                    new_status, feedback = "sl_hit", "incorrect"
            
            elif signal_type == "sell":
                if current_price <= tp:
                    new_status, feedback = "tp_hit", "correct"
                elif current_price >= sl:
                    new_status, feedback = "sl_hit", "incorrect"

            if new_status:
                print(f"✅ OUTCOME: Signal {signal_id} resulted in '{new_status}' at price {current_price:.5f}.")
                update_signal_status(signal_id, new_status, current_price)
                save_feedback(symbol, feedback, timeframe)

    print(f"--- [{datetime.now()}] Signal Checker Job Finished ---")
    
