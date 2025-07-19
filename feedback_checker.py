import httpx
from datetime import datetime, timedelta
from typing import Union, Dict, Any

# ہمارے پروجیکٹ کے ایجنٹس
# --- درست امپورٹ لائنز ---
from signal_tracker import get_active_signals, move_signal_to_completed
from feedback_memory import save_feedback
from key_manager import get_api_key, mark_key_as_limited

async def fetch_current_price_twelve_data(symbol: str, client: httpx.AsyncClient) -> Union[float, None]:
    """
    Twelve Data API سے تازہ ترین قیمت حاصل کرتا ہے۔
    """
    api_key = get_api_key()
    if not api_key:
        print("FeedbackChecker: All API keys are limited. Cannot fetch price.")
        return None
    
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={api_key}"
    try:
        response = await client.get(url, timeout=10)
        if response.status_code == 429:
            print(f"FeedbackChecker: API key limit reached for key ...{api_key[-4:]}. Rotating.")
            mark_key_as_limited(api_key)
            return await fetch_current_price_twelve_data(symbol, client) # دوسری کلید کے ساتھ دوبارہ کوشش کریں
        
        response.raise_for_status()
        data = response.json()
        price = data.get("price")
        return float(price) if price else None
    except Exception as e:
        print(f"⚠️ FeedbackChecker: Error fetching price for {symbol}: {e}")
        return None

async def check_active_signals_job():
    """
    تمام فعال سگنلز کو چیک کرتا ہے، ان کا نتیجہ طے کرتا ہے، اور فیڈ بیک محفوظ کرتا ہے۔
    """
    print(f"[{datetime.now()}] --- Feedback Checker: Starting job... ---")
    # --- درست فنکشن کا نام ---
    active_signals = get_active_signals()
    if not active_signals:
        print("Feedback Checker: No active signals to check.")
        return

    print(f"Feedback Checker: Found {len(active_signals)} active signals to check.")
    async with httpx.AsyncClient() as client:
        for signal in active_signals:
            signal_id = signal.get("id")
            symbol = signal.get("symbol")
            signal_type = signal.get("signal")
            tp = signal.get("tp")
            sl = signal.get("sl")
            signal_time_str = signal.get("timestamp")

            if not all([signal_id, symbol, signal_type, tp, sl, signal_time_str]):
                continue

            current_price = await fetch_current_price_twelve_data(symbol, client)
            if current_price is None:
                continue

            print(f"Checking {signal_id} for {symbol}. Price: {current_price}, TP: {tp}, SL: {sl}")
            
            outcome, new_status = None, None
            if signal_type == "buy":
                if current_price >= tp:
                    outcome, new_status = "correct", "tp_hit"
                elif current_price <= sl:
                    outcome, new_status = "incorrect", "sl_hit"
            elif signal_type == "sell":
                if current_price <= tp:
                    outcome, new_status = "correct", "tp_hit"
                elif current_price >= sl:
                    outcome, new_status = "incorrect", "sl_hit"
            
            signal_time = datetime.fromisoformat(signal_time_str)
            if new_status is None and (datetime.utcnow() - signal_time) > timedelta(hours=24):
                outcome, new_status = "missed", "expired"
            
            if outcome and new_status:
                print(f"Signal {signal_id} outcome: {new_status}. Saving feedback: '{outcome}'")
                save_feedback(symbol, signal.get('timeframe', 'N/A'), outcome)
                # --- درست فنکشن کا نام ---
                move_signal_to_completed(signal_id, new_status, outcome)

    print(f"[{datetime.now()}] --- Feedback Checker Finished ---")
                    
