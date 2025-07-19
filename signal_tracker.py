import json
import os
from datetime import datetime
from typing import Dict, Any, List

# --- اہم: فائل کا نام اور راستہ ---
# یہ فائل اب صرف لائیو سگنل کو محفوظ کرے گی
LIVE_SIGNAL_FILE = "live_signal.json"
DATA_DIR = "data"

# ڈائریکٹری کو یقینی بنائیں
os.makedirs(DATA_DIR, exist_ok=True)
LIVE_SIGNAL_FILE_PATH = os.path.join(DATA_DIR, LIVE_SIGNAL_FILE)

# --- ایکٹو سگنلز کو ٹریک کرنے کے لیے فائلیں (فیڈ بیک کے لیے) ---
ACTIVE_TRADES_FILE = "active_trades.json"
COMPLETED_TRADES_FILE = "completed_trades.json"
ACTIVE_TRADES_FILE_PATH = os.path.join(DATA_DIR, ACTIVE_TRADES_FILE)
COMPLETED_TRADES_FILE_PATH = os.path.join(DATA_DIR, COMPLETED_TRADES_FILE)

# --- فائل کی ابتدائی تشکیل ---
def initialize_json_file(file_path: str, default_content: Any):
    if not os.path.exists(file_path):
        try:
            with open(file_path, "w") as f:
                json.dump(default_content, f, indent=2)
            print(f"✅ Created empty file: {file_path}")
        except Exception as e:
            print(f"⚠️ Error creating file {file_path}: {e}")

# تمام فائلوں کو شروع کریں
initialize_json_file(LIVE_SIGNAL_FILE_PATH, {"signal": "wait", "reason": "Initializing..."})
initialize_json_file(ACTIVE_TRADES_FILE_PATH, [])
initialize_json_file(COMPLETED_TRADES_FILE_PATH, [])


# --- لائیو سگنل کے فنکشنز (جو غائب تھے) ---
def set_live_signal(signal_data: Dict[str, Any]):
    """
    موجودہ لائیو سگنل کو فائل میں محفوظ کرتا ہے۔
    """
    try:
        # سگنل میں ٹائم اسٹیمپ شامل کریں تاکہ پتہ چلے یہ کب بنا تھا
        signal_data["found_at"] = datetime.utcnow().strftime("%H:%M:%S")
        with open(LIVE_SIGNAL_FILE_PATH, "w") as f:
            json.dump(signal_data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Error setting live signal: {e}")

def get_live_signal() -> Dict[str, Any]:
    """
    فائل سے موجودہ لائیو سگنل حاصل کرتا ہے۔
    """
    try:
        with open(LIVE_SIGNAL_FILE_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # اگر فائل موجود نہیں یا خالی ہے تو ڈیفالٹ سگنل واپس کریں
        return {"signal": "wait", "reason": "Signal file not found or is empty."}


# --- ایکٹو اور مکمل شدہ ٹریڈز کے فنکشنز ---
def add_active_signal(signal_data: Dict[str, Any]):
    """
    ایک نئے فعال سگنل کو ٹریکر میں شامل کرتا ہے۔
    """
    try:
        with open(ACTIVE_TRADES_FILE_PATH, "r") as f:
            active_signals = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        active_signals = []

    signal_id = f"{signal_data['symbol'].replace('/', '_')}_{datetime.utcnow().timestamp()}"
    signal_data['id'] = signal_id
    signal_data['status'] = 'active'
    signal_data['timestamp'] = datetime.utcnow().isoformat()
    
    # صرف ضروری معلومات محفوظ کریں
    trade_entry = {
        "id": signal_data['id'],
        "symbol": signal_data['symbol'],
        "timeframe": signal_data['timeframe'],
        "signal": signal_data['signal'],
        "price": signal_data['price'],
        "tp": signal_data['tp'],
        "sl": signal_data['sl'],
        "timestamp": signal_data['timestamp'],
        "status": signal_data['status']
    }
    active_signals.append(trade_entry)

    try:
        with open(ACTIVE_TRADES_FILE_PATH, "w") as f:
            json.dump(active_signals, f, indent=2)
        print(f"✅ New active trade added to tracker: {signal_id}")
    except Exception as e:
        print(f"⚠️ Error saving active trade: {e}")

def get_active_signals() -> List[Dict[str, Any]]:
    try:
        with open(ACTIVE_TRADES_FILE_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def move_signal_to_completed(signal_id: str, new_status: str, outcome: str):
    try:
        with open(ACTIVE_TRADES_FILE_PATH, "r") as f:
            active_signals = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return

    signal_to_move = None
    remaining_signals = []
    for signal in active_signals:
        if signal.get('id') == signal_id:
            signal_to_move = signal
        else:
            remaining_signals.append(signal)

    if signal_to_move:
        signal_to_move['status'] = new_status
        signal_to_move['outcome'] = outcome
        signal_to_move['completed_at'] = datetime.utcnow().isoformat()

        try:
            with open(COMPLETED_TRADES_FILE_PATH, "r") as f:
                completed_signals = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            completed_signals = []
        
        completed_signals.insert(0, signal_to_move) # نیا سب سے اوپر

        with open(COMPLETED_TRADES_FILE_PATH, "w") as f:
            json.dump(completed_signals, f, indent=2)
            
        with open(ACTIVE_TRADES_FILE_PATH, "w") as f:
            json.dump(remaining_signals, f, indent=2)
            
        print(f"✅ Signal {signal_id} moved to completed with status: {new_status}")

def get_completed_signals() -> List[Dict[str, Any]]:
    try:
        with open(COMPLETED_TRADES_FILE_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
                      
