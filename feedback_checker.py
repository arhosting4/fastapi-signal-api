import httpx
from datetime import datetime, timedelta
from typing import Optional

from signal_tracker import get_all_signals, update_signal_status
from feedback_memory import save_feedback # یہ اب بھی وہی رہے گا
from key_manager import key_manager

async def fetch_current_price_twelve_data(symbol: str, client: httpx.AsyncClient) -> Optional[float]:
    api_key = key_manager.get_current_key()
    if not api_key: return None
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={api_key}"
    try:
        response = await client.get(url, timeout=10)
        if response.status_code == 429:
            key_manager.rotate_to_next_key()
            return None
        response.raise_for_status()
        data = response.json()
        return float(data["price"]) if "price" in data else None
    except Exception as e:
        print(f"⚠️ Price fetch error in checker: {e}")
        return None

async def check_active_signals_job():
    """
    تمام فعال سگنلز کی نگرانی کرتا ہے اور نتیجہ کی بنیاد پر فیڈ بیک محفوظ کرتا ہے۔
    """
    print("--- FEEDBACK CHECKER: Running job... ---")
    active_signals = get_all_signals()
    if not active_signals:
        print("--- FEEDBACK CHECKER: No active signals to check. ---")
        return

    async with httpx.AsyncClient() as client:
        for signal in active_signals:
            symbol = signal.get("symbol")
            timeframe = signal.get("timeframe") # <-- ٹائم فریم حاصل کریں
            if not all([symbol, timeframe, signal.get("id"), signal.get("signal"), signal.get("tp"), signal.get("sl")]):
                continue

            current_price = await fetch_current_price_twelve_data(symbol, client)
            if current_price is None: continue

            feedback, new_status = None, None
            signal_type = signal["signal"]
            tp, sl = signal["tp"], signal["sl"]

            if signal_type == "buy":
                if current_price >= tp: feedback, new_status = "correct", "tp_hit"
                elif current_price <= sl: feedback, new_status = "incorrect", "sl_hit"
            elif signal_type == "sell":
                if current_price <= tp: feedback, new_status = "correct", "tp_hit"
                elif current_price >= sl: feedback, new_status = "incorrect", "sl_hit"
            
            signal_time = datetime.fromisoformat(signal.get("timestamp"))
            if new_status is None and (datetime.utcnow() - signal_time) > timedelta(hours=4):
                feedback, new_status = "expired", "expired"
            
            if feedback and new_status:
                # --- اہم تبدیلی: پرفارمنس کی بنائیں اور استعمال کریں ---
                performance_key = f"{symbol}_{timeframe}"
                save_feedback(performance_key, feedback)
                update_signal_status(signal["id"], new_status, current_price)
                print(f"--- FEEDBACK CHECKER: Signal {signal['id']} outcome: {new_status}. Feedback saved for '{performance_key}'. ---")
                
