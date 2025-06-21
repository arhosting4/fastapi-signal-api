# agents/logger.py

import os
import json
from datetime import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def log_signal(symbol, result, candles):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    entry = {
        "timestamp": timestamp,
        "symbol": symbol,
        "signal": result.get("signal"),
        "risk": result.get("risk"),
        "pattern": result.get("pattern"),
        "news": result.get("news"),
        "confidence": result.get("confidence"),
        "tier": result.get("tier"),
        "reason": result.get("reason"),
        "candles": candles  # Optional: comment out if large
    }

    log_file = os.path.join(LOG_DIR, f"{symbol.replace('/', '_')}_log.jsonl")
    
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
