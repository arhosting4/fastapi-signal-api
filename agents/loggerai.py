# agents/loggerai.py
import json
from datetime import datetime
import os

LOG_FILE = "signal_logs.jsonl"

def log_signal(data: dict):
    data["timestamp"] = datetime.utcnow().isoformat()

    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(data) + "\n")
    except Exception as e:
        print(f"Log error: {e}")
