from datetime import datetime
from typing import List, Dict, Optional, Any

LIVE_SIGNAL_CACHE: Dict[str, Any] = {}
ACTIVE_SIGNALS_CACHE: List[Dict[str, Any]] = []

def set_live_signal(signal_data: Dict[str, Any]):
    global LIVE_SIGNAL_CACHE
    LIVE_SIGNAL_CACHE = signal_data

def get_live_signal() -> Optional[Dict[str, Any]]:
    return LIVE_SIGNAL_CACHE

def add_active_signal(signal_data: Dict[str, Any]):
    global ACTIVE_SIGNALS_CACHE
    signal_id = f"{signal_data['symbol']}_{datetime.utcnow().timestamp()}"
    signal_data['signal_id'] = signal_id
    signal_data['timestamp'] = datetime.utcnow().isoformat()
    ACTIVE_SIGNALS_CACHE.append(signal_data)

def remove_active_signal(signal_id: str):
    global ACTIVE_SIGNALS_CACHE
    ACTIVE_SIGNALS_CACHE = [s for s in ACTIVE_SIGNALS_CACHE if s.get('signal_id') != signal_id]

def get_all_signals() -> List[Dict[str, Any]]:
    return list(ACTIVE_SIGNALS_CACHE)

def get_active_signals_count() -> int:
    return len(ACTIVE_SIGNALS_CACHE)
    
