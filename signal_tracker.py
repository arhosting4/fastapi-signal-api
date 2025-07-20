# filename: signal_tracker.py

from datetime import datetime
from typing import List, Dict, Any, Optional

# --- یہ وہ کیش ہے جہاں تمام فعال سگنلز محفوظ ہوتے ہیں ---
ACTIVE_SIGNALS_CACHE: List[Dict[str, Any]] = []

def add_active_signal(signal_data: Dict[str, Any]):
    """
    ایک نئے فعال سگنل کو کیش میں شامل کرتا ہے۔
    یہ فنکشن hunter.py کے ذریعے استعمال کیا جاتا ہے۔
    """
    global ACTIVE_SIGNALS_CACHE
    # ہر سگنل کو ایک منفرد شناخت دیں تاکہ اسے بعد میں ٹریک کیا جا سکے
    signal_id = f"{signal_data['symbol']}_{signal_data['timeframe']}_{datetime.utcnow().timestamp()}"
    signal_data['signal_id'] = signal_id
    signal_data['timestamp'] = datetime.utcnow().isoformat()
    ACTIVE_SIGNALS_CACHE.append(signal_data)
    print(f"--- Signal Tracker: Added new signal {signal_id}. Total active signals: {len(ACTIVE_SIGNALS_CACHE)} ---")

def remove_active_signal(signal_id: str):
    """
    ایک سگنل کو اس کی شناخت کی بنیاد پر کیش سے ہٹاتا ہے۔
    یہ فنکشن feedback_checker.py کے ذریعے استعمال کیا جاتا ہے۔
    """
    global ACTIVE_SIGNALS_CACHE
    initial_count = len(ACTIVE_SIGNALS_CACHE)
    ACTIVE_SIGNALS_CACHE = [s for s in ACTIVE_SIGNALS_CACHE if s.get('signal_id') != signal_id]
    if len(ACTIVE_SIGNALS_CACHE) < initial_count:
        print(f"--- Signal Tracker: Removed signal {signal_id}. Total active signals: {len(ACTIVE_SIGNALS_CACHE)} ---")

def get_all_signals() -> List[Dict[str, Any]]:
    """
    تمام فعال سگنلز کی فہرست لوٹاتا ہے۔
    یہ فنکشن feedback_checker.py اور API اینڈ پوائنٹ کے ذریعے استعمال کیا جاتا ہے۔
    """
    return list(ACTIVE_SIGNALS_CACHE)

def get_active_signals_count() -> int:
    """
    فعال سگنلز کی کل تعداد لوٹاتا ہے۔
    یہ فنکشن hunter.py کے ذریعے استعمال کیا جاتا ہے۔
    """
    return len(ACTIVE_SIGNALS_CACHE)

# --- اہم نوٹ: get_live_signal اور set_live_signal کو ہٹا دیا گیا ہے ---
# کیونکہ اب ہم ملٹی سگنل موڈ میں ہیں اور یہ اب غیر ضروری ہیں۔
