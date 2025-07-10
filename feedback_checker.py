import sys
sys.path.append('.') # Add the root directory to the Python path

import os
import httpx
import asyncio
from datetime import datetime, timedelta
from src.agents.signal_tracker import get_active_signals, update_signal_status
from src.agents.feedback_memory import save_feedback

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

async def fetch_current_price(symbol: str) -> float | None:
    """Fetches the most recent price for a symbol from Twelve Data."""
    if not TWELVE_DATA_API_KEY:
        print("⚠️ TWELVE_DATA_API_KEY is not set.")
        return None

    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_DATA_API_KEY}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data.get("price"))
    except Exception as e:
        print(f"⚠️ Error fetching current price for {symbol}: {e}")
        return None

async def check_signals():
    """
    Checks all active signals, determines their outcome, and saves feedback.
    """
    print(f"[{datetime.now()}] --- Running Feedback Checker (Background Task) ---")
    active_signals = get_active_signals()

    if not active_signals:
        print("No active signals to check.")
        return

    print(f"Found {len(active_signals)} active signals to check.")

    for signal in active_signals:
        signal_id = signal.get("id")
        symbol = signal.get("symbol")
        signal_type = signal.get("signal")
        tp = signal.get("tp")
        sl = signal.get("sl")
        signal_time_str = signal.get("timestamp")
        
        if not all([signal_id, symbol, signal_type, tp, sl, signal_time_str]):
            print(f"Skipping invalid signal: {signal_id}")
            continue

        # Fetch the current market price
        current_price = await fetch_current_price(symbol)
        if current_price is None:
            print(f"Could not fetch price for {symbol}. Skipping check for signal {signal_id}.")
            continue

        print(f"Checking signal {signal_id} for {symbol}. Current Price: {current_price}, TP: {tp}, SL: {sl}")

        feedback = None
        new_status = None

        # Check for TP/SL hit
        if signal_type == "buy":
            if current_price >= tp:
                feedback = "correct"
                new_status = "tp_hit"
            elif current_price <= sl:
                feedback = "incorrect"
                new_status = "sl_hit"
        elif signal_type == "sell":
            if current_price <= tp:
                feedback = "correct"
                new_status = "tp_hit"
            elif current_price >= sl:
                feedback = "incorrect"
                new_status = "sl_hit"

        # Check for signal expiration (e.g., after 24 hours)
        signal_time = datetime.fromisoformat(signal_time_str)
        if new_status is None and (datetime.utcnow() - signal_time) > timedelta(hours=24):
            feedback = "missed" # Or 'expired'
            new_status = "expired"

        # If feedback was determined, save it and update the signal status
        if feedback and new_status:
            print(f"Signal {signal_id} outcome: {new_status}. Saving feedback: '{feedback}'")
            save_feedback(symbol, feedback)
            update_signal_status(signal_id, new_status)

    print(f"[{datetime.now()}] --- Feedback Checker Finished (Background Task) ---")
        
