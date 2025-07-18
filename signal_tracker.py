import json
import os
from datetime import datetime

TRACKER_FILE = "signal_tracker.json"
TRACKER_DIR = "data"

os.makedirs(TRACKER_DIR, exist_ok=True)
TRACKER_FILE_PATH = os.path.join(TRACKER_DIR, TRACKER_FILE)

# فائل کو شروع میں خالی لسٹ کے ساتھ بنائیں
if not os.path.exists(TRACKER_FILE_PATH):
    with open(TRACKER_FILE_PATH, "w") as f:
        json.dump([], f)

def get_all_signals() -> list:
    """ ٹریکر سے تمام سگنلز (فعال اور غیر فعال) حاصل کرتا ہے۔ """
    try:
        with open(TRACKER_FILE_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_all_signals(signals: list):
    """ تمام سگنلز کی فہرست کو فائل میں محفوظ کرتا ہے۔ """
    try:
        with open(TRACKER_FILE_PATH, "w") as f:
            json.dump(signals, f, indent=2)
    except Exception as e:
        print(f"⚠️ Error saving signals: {e}")

# --- نیا فنکشن ---
def get_active_signal_for_timeframe(symbol: str, timeframe: str):
    """
    ایک مخصوص علامت اور ٹائم فریم کے لیے فعال سگنل تلاش کرتا ہے۔
    اگر مل جائے تو سگنل ڈکشنری واپس کرتا ہے، ورنہ None۔
    """
    signals = get_all_signals()
    for signal in signals:
        if (signal.get('status') == 'active' and
            signal.get('symbol') == symbol and
            signal.get('timeframe') == timeframe):
            print(f"✅ Found active signal {signal.get('id')} for {symbol} on {timeframe}.")
            return signal
    return None

def add_active_signal(signal_data: dict):
    """ ایک نئے فعال سگنل کو ٹریکر میں شامل کرتا ہے۔ """
    signals = get_all_signals()
    
    signal_id = f"{signal_data['symbol'].replace('/', '_')}_{datetime.utcnow().timestamp()}"
    signal_data['id'] = signal_id
    signal_data['status'] = 'active'
    signal_data['timestamp'] = datetime.utcnow().isoformat()

    signals.append(signal_data)
    save_all_signals(signals)
    print(f"✅ New active signal added to tracker: {signal_id}")

def update_signal_status(signal_id: str, new_status: str, outcome_price: float):
    """ سگنل کی حیثیت کو اپ ڈیٹ کرتا ہے اور اسے غیر فعال کرتا ہے۔ """
    signals = get_all_signals()
    signal_found = False
    for signal in signals:
        if signal.get('id') == signal_id:
            signal['status'] = new_status
            signal['outcome_price'] = outcome_price
            signal['closed_at'] = datetime.utcnow().isoformat()
            signal_found = True
            break
    
    if signal_found:
        save_all_signals(signals)
        print(f"✅ Signal {signal_id} status updated to {new_status}.")

