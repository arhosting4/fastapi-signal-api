# filename: signal_tracker.py

from datetime import datetime
from typing import List, Dict, Any, Optional

# --- اہم تبدیلی: کیش کو اب سگنلز کی فہرست ذخیرہ کرنے کے لیے ڈیزائن کیا گیا ہے ---
LIVE_SIGNALS_CACHE: List[Dict[str, Any]] = []
ACTIVE_SIGNALS_CACHE: List[Dict[str, Any]] = []

def set_live_signals(signals_data: List[Dict[str, Any]]):
    """
    لائیو سگنلز کی پوری فہرست کو سیٹ کرتا ہے۔
    """
    global LIVE_SIGNALS_CACHE
    LIVE_SIGNALS_CACHE = signals_data

def get_live_signals() -> List[Dict[str, Any]]:
    """
    تمام لائیو سگنلز کی فہرست لوٹاتا ہے۔
    """
    return LIVE_SIGNALS_CACHE

def add_active_signals(signals_data: List[Dict[str, Any]]):
    """
    فعال سگنلز کی فہرست میں نئے سگنلز شامل کرتا ہے۔
    """
    global ACTIVE_SIGNALS_CACHE
    for signal_data in signals_data:
        # یقینی بنائیں کہ ایک ہی سگنل دوبارہ شامل نہ ہو
        if not any(s['symbol'] == signal_data['symbol'] and s['timeframe'] == signal_data['timeframe'] for s in ACTIVE_SIGNALS_CACHE):
            signal_id = f"{signal_data['symbol']}_{signal_data['timeframe']}_{datetime.utcnow().timestamp()}"
            signal_data['signal_id'] = signal_id
            signal_data['timestamp'] = datetime.utcnow().isoformat()
            ACTIVE_SIGNALS_CACHE.append(signal_data)

def remove_active_signal(signal_id: str):
    """
    ایک فعال سگنل کو اس کی ID کی بنیاد پر ہٹاتا ہے۔
    """
    global ACTIVE_SIGNALS_CACHE
    ACTIVE_SIGNALS_CACHE = [s for s in ACTIVE_SIGNALS_CACHE if s.get('signal_id') != signal_id]

def get_all_active_signals() -> List[Dict[str, Any]]:
    """
    تمام فعال سگنلز کی فہرست لوٹاتا ہے۔
    """
    return list(ACTIVE_SIGNALS_CACHE)

def get_active_signals_count() -> int:
    """
    فعال سگنلز کی تعداد لوٹاتا ہے۔
    """
    return len(ACTIVE_SIGNALS_CACHE)
    
