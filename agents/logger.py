# src/agents/logger.py

import os
import json
from datetime import datetime

LOG_DIR = "logs" # Directory where log files will be stored

# Ensure the log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

def log_signal(symbol: str, result: dict, candles: list):
    """
    Logs the generated signal and its context to a JSONL file.
    Each signal is logged as a separate JSON object on a new line.

    Parameters:
        symbol (str): The trading pair symbol.
        result (dict): The dictionary containing the final signal result from fusion_engine.
        candles (list): The OHLC candles used to generate the signal.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Prepare the log entry
    entry = {
        "timestamp": timestamp,
        "symbol": symbol,
        "signal": result.get("signal"),
        "status": result.get("status"),
        "error": result.get("error"), # Log error messages if status is not 'ok'
        "pattern": result.get("pattern"),
        "risk": result.get("risk"),
        "news": result.get("news"),
        "confidence": result.get("confidence"),
        "tier": result.get("tier"),
        "reason": result.get("reason"),
        "price_at_signal": float(candles[-1].get("close")) if candles else None, # Log the closing price at signal time
        # "candles": candles # Uncomment if you want to log the full candle data (can be large)
    }

    # Create a log file name based on the symbol
    # Replace '/' with '_' for valid file names (e.g., XAU_USD_log.jsonl)
    log_file = os.path.join(LOG_DIR, f"{symbol.replace('/', '_')}_log.jsonl")
    
    try:
        with open(log_file, "a") as f: # Open in append mode
            f.write(json.dumps(entry) + "\n")
        print(f"✅ Signal logged for {symbol} to {log_file}")
    except Exception as e:
        print(f"⚠️ Log error for {symbol}: {e}")

