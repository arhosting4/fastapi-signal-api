# filename: signal_tracker.py

from datetime import datetime
from typing import List, Dict, Any

ACTIVE_SIGNALS_CACHE: List[Dict[str, Any]] = []

def add_active_signal(signal_data: Dict[str, Any]):
    global ACTIVE_SIGNALS_CACHE
    signal_id = f"{signal_data['symbol']}_{signal_data['timeframe']}_{datetime.utcnow().timestamp()}"
    signal_data['signal_id'] = signal_id
    signal_data['timestamp'] = datetime.utcnow().isoformat()
    ACTIVE_SIGNALS_CACHE.append(signal_data)
    print(f"--- Signal Tracker: Added new signal {signal_id}. Total active: {len(ACTIVE_SIGNALS_CACHE)} ---")

def remove_active_signal(signal_id: str):
    global ACTIVE_SIGNALS_CACHE
    initial_count = len(ACTIVE_SIGNALS_CACHE)
    ACTIVE_SIGNALS_CACHE = [s for s in ACTIVE_SIGNALS_CACHE if s.get('signal_id') != signal_id]
    if len(ACTIVE_SIGNALS_CACHE) < initial_count:
        print(f"--- Signal Tracker: Removed signal {signal_id}. Total active: {len(ACTIVE_SIGNALS_CACHE)} ---")

def get_all_signals() -> List[Dict[str, Any]]:
    return list(ACTIVE_SIGNALS_CACHE)

def get_active_signals_count() -> int:
    return len(ACTIVE_SIGNALS_CACHE)
    
