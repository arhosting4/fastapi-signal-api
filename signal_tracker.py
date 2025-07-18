import json
import os
from datetime import datetime

# --- فائل کے نام ---
ACTIVE_SIGNALS_FILE = "data/active_signals.json"
LIVE_SIGNAL_FILE = "data/live_signal.json" # بہترین سگنل کے لیے نئی فائل

# یقینی بنائیں کہ 'data' ڈائرکٹری موجود ہے
os.makedirs("data", exist_ok=True)

# --- لائیو سگنل کے لیے فنکشنز ---

def save_live_signal(signal_data: dict):
    """
    AI ہنٹر کے ذریعے منتخب کردہ بہترین سگنل کو ایک مخصوص فائل میں محفوظ کرتا ہے۔
    """
    try:
        # سگنل میں ایک ٹائم اسٹیمپ شامل کریں تاکہ پتہ چلے یہ کب بنا تھا
        signal_data['generated_at'] = datetime.utcnow().isoformat()
        with open(LIVE_SIGNAL_FILE, "w") as f:
            json.dump(signal_data, f, indent=2)
        print(f"LIVE SIGNAL: Saved '{signal_data.get('signal')}' on {signal_data.get('symbol')} to {LIVE_SIGNAL_FILE}")
    except Exception as e:
        print(f"ERROR: Could not save live signal. Reason: {e}")

def get_live_signal() -> dict:
    """
    محفوظ کردہ لائیو سگنل کو پڑھتا ہے تاکہ فرنٹ اینڈ کو دکھایا جا سکے۔
    """
    if not os.path.exists(LIVE_SIGNAL_FILE):
        # اگر فائل موجود نہیں، تو ایک ڈیفالٹ "WAIT" سگنل بھیجیں
        return {
            "signal": "wait",
            "reason": "AI Engine is starting up. Please wait for the first signal.",
            "symbol": "N/A"
        }
    try:
        with open(LIVE_SIGNAL_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"signal": "wait", "reason": "Could not read live signal data."}

# --- فعال سگنلز کی نگرانی کے لیے پرانے فنکشنز (یہ ویسے ہی رہیں گے) ---

def add_active_signal(signal_data: dict):
    """
    ایک نئے فعال سگنل کو ٹریکر میں شامل کرتا ہے (جب TP/SL کی نگرانی شروع ہوتی ہے)۔
    """
    try:
        with open(ACTIVE_SIGNALS_FILE, "r") as f:
            active_signals = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        active_signals = []

    signal_id = f"{signal_data['symbol'].replace('/', '_')}_{datetime.utcnow().timestamp()}"
    signal_data['id'] = signal_id
    signal_data['status'] = 'active'
    signal_data['timestamp'] = datetime.utcnow().isoformat()

    active_signals.append(signal_data)

    with open(ACTIVE_SIGNALS_FILE, "w") as f:
        json.dump(active_signals, f, indent=2)
    print(f"ACTIVE SIGNAL: Added {signal_id} to tracker for monitoring.")

def get_all_signals() -> list:
    """تمام فعال سگنلز کو ٹریکر سے حاصل کرتا ہے۔"""
    try:
        with open(ACTIVE_SIGNALS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def update_signal_status(signal_id: str, new_status: str, closing_price: float):
    """ٹریکر میں سگنل کی حیثیت کو اپ ڈیٹ کرتا ہے۔"""
    signals = get_all_signals()
    signal_found = False
    for signal in signals:
        if signal.get('id') == signal_id:
            signal['status'] = new_status
            signal['closing_price'] = closing_price
            signal['closed_at'] = datetime.utcnow().isoformat()
            signal_found = True
            break
    
    # صرف فعال سگنلز کو فائل میں واپس لکھیں
    updated_signals = [s for s in signals if s.get('status') == 'active']
    
    if signal_found:
        with open(ACTIVE_SIGNALS_FILE, "w") as f:
            json.dump(updated_signals, f, indent=2)
        print(f"SIGNAL STATUS: Updated {signal_id} to {new_status} and removed from active list.")

