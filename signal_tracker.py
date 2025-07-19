# filename: signal_tracker.py
import json
import os
from typing import List, Dict, Any

DATA_DIR = "data"
ACTIVE_SIGNALS_FILE = os.path.join(DATA_DIR, "active_signals.json")

# --- اہم ترین تبدیلی: یقینی بنائیں کہ 'data' فولڈر موجود ہے ---
os.makedirs(DATA_DIR, exist_ok=True)

def _ensure_file_exists(file_path: str, default_content: Any):
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump(default_content, f, indent=2)
        print(f"✅ Created empty file: {file_path}")

def set_active_signals(signals: List[Dict[str, Any]]):
    _ensure_file_exists(ACTIVE_SIGNALS_FILE, [])
    try:
        with open(ACTIVE_SIGNALS_FILE, "w") as f:
            json.dump(signals, f, indent=2)
        print(f"--- INFO: Wrote {len(signals)} active signals to file. ---")
    except Exception as e:
        print(f"--- ERROR: Could not write active signals to file: {e} ---")

def get_active_signals() -> List[Dict[str, Any]]:
    _ensure_file_exists(ACTIVE_SIGNALS_FILE, [])
    try:
        with open(ACTIVE_SIGNALS_FILE, "r") as f:
            content = f.read()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

_ensure_file_exists(ACTIVE_SIGNALS_FILE, [])
