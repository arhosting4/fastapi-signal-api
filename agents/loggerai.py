# src/agents/logger.py

import datetime
import json
import os

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "signals_log.json")

# Ensure the directory exists
os.makedirs(LOG_DIR, exist_ok=True)

def log_signal(data: dict) -> None:
    """
    Appends the signal details to a JSON log file.
    Includes timestamp and all core signal metadata.
    """
    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "symbol": data.get("symbol"),
        "signal": data.get("signal"),
        "pattern": data.get("pattern"),
        "risk": data.get("risk"),
        "news": data.get("news"),
        "reason": data.get("reason"),
        "confidence": data.get("confidence"),
        "tier": data.get("tier")
    }

    try:
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w") as f:
                json.dump([log_entry], f, indent=4)
        else:
            with open(LOG_FILE, "r+") as f:
                logs = json.load(f)
                logs.append(log_entry)
                f.seek(0)
                json.dump(logs, f, indent=4)
    except Exception as e:
        print(f"⚠️ Log writing failed: {e}")
