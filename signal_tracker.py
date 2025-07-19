# signal_tracker.py

import json
import os
from typing import List, Dict, Any

# --- اہم تبدیلی: فائل کا نام اور راستہ ---
DATA_DIR = "data"
ACTIVE_SIGNALS_FILE = os.path.join(DATA_DIR, "active_signals.json")

def _ensure_file_exists(file_path: str, default_content: Any):
    """یقینی بناتا ہے کہ فائل موجود ہے، اگر نہیں تو اسے ڈیفالٹ مواد سے بناتا ہے۔"""
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(default_content, f, indent=2)
        print(f"✅ Created empty file: {file_path}")

def set_active_signals(signals: List[Dict[str, Any]]):
    """
    فعال سگنلز کی پوری فہرست کو فائل میں محفوظ کرتا ہے۔
    یہ پرانے سگنلز کو اوور رائٹ کر دے گا۔
    """
    _ensure_file_exists(ACTIVE_SIGNALS_FILE, [])
    try:
        with open(ACTIVE_SIGNALS_FILE, "w") as f:
            json.dump(signals, f, indent=2)
        print(f"--- INFO: Wrote {len(signals)} active signals to file. ---")
    except Exception as e:
        print(f"--- ERROR: Could not write active signals to file: {e} ---")

def get_active_signals() -> List[Dict[str, Any]]:
    """
    فائل سے فعال سگنلز کی فہرست پڑھتا ہے۔
    """
    _ensure_file_exists(ACTIVE_SIGNALS_FILE, [])
    try:
        with open(ACTIVE_SIGNALS_FILE, "r") as f:
            # --- اہم: اگر فائل خالی ہے تو خالی فہرست واپس کریں ---
            content = f.read()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def clear_active_signals():
    """
    تمام فعال سگنلز کو صاف کرتا ہے (خالی فہرست لکھتا ہے)۔
    """
    set_active_signals([])

# --- اس بات کو یقینی بنائیں کہ ایپ کے آغاز پر فائل موجود ہو ---
_ensure_file_exists(ACTIVE_SIGNALS_FILE, [])
        
