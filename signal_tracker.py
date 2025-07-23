# filename: signal_tracker.py

from datetime import datetime
from typing import List, Dict, Any

# --- عارضی طور پر RAM میں فعال سگنلز محفوظ کیے جاتے ہیں ---
ACTIVE_SIGNALS_CACHE: List[Dict[str, Any]] = []

def add_active_signal(signal_data: Dict[str, Any]):
    """
    سگنل کو ایک منفرد ID دے کر فعال فہرست میں شامل کرتا ہے۔
    """
    global ACTIVE_SIGNALS_CACHE
    signal_id = f"{signal_data['symbol']}_{signal_data['timeframe']}_{datetime.utcnow().timestamp()}"
    signal_data['signal_id'] = signal_id
    signal_data['timestamp'] = datetime.utcnow().isoformat()
    ACTIVE_SIGNALS_CACHE.append(signal_data)
    print(f"--- Signal Tracker: Added new signal {signal_id}. Total active: {len(ACTIVE_SIGNALS_CACHE)} ---")

def remove_active_signal(signal_id: str):
    """
    فعال سگنل کی فہرست سے دیے گئے ID کے سگنل کو ہٹا دیتا ہے۔
    """
    global ACTIVE_SIGNALS_CACHE
    initial_count = len(ACTIVE_SIGNALS_CACHE)
    ACTIVE_SIGNALS_CACHE = [s for s in ACTIVE_SIGNALS_CACHE if s.get('signal_id') != signal_id]
    if len(ACTIVE_SIGNALS_CACHE) < initial_count:
        print(f"--- Signal Tracker: Removed signal {signal_id}. Total active: {len(ACTIVE_SIGNALS_CACHE)} ---")

def get_all_signals() -> List[Dict[str, Any]]:
    """تمام فعال سگنلز کی فہرست واپس کرتا ہے۔"""
    return list(ACTIVE_SIGNALS_CACHE)

def get_active_signals_count() -> int:
    """فعلاً موجود سگنلز کی کل تعداد واپس کرتا ہے۔"""
    return len(ACTIVE_SIGNALS_CACHE)
