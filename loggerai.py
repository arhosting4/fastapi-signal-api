# src/agents/loggerai.py

import datetime

memory = []

def log_signal(symbol: str, signal: str, confidence: float, pattern: str, risk: str, reason: str, tier: str):
    """
    Logs the final signal with metadata to in-memory store.
    """
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    entry = {
        "time": timestamp,
        "symbol": symbol,
        "signal": signal,
        "confidence": round(confidence * 100, 2),
        "pattern": pattern,
        "risk": risk,
        "reason": reason,
        "tier": tier
    }

    memory.append(entry)

def get_latest_logs(n: int = 5):
    """
    Returns the last n logs.
    """
    return memory[-n:]
