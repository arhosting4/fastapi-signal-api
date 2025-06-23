# agents/trainerai.py

import json
import os
from datetime import datetime

MEMORY_FILE = "signal_memory.json"

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []

    with open(MEMORY_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_memory(memory: list):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory[-200:], f, indent=2)  # Keep last 200 only

def learn_from_history(symbol: str, signal: str, price: float, tf: str) -> str:
    """
    Simulates adaptive learning based on previous signals' outcome.
    Returns 'support', 'reject', or 'uncertain' to guide final signal.
    """
    memory = load_memory()
    now = datetime.utcnow().isoformat()

    # Log new decision
    memory.append({
        "timestamp": now,
        "symbol": symbol,
        "signal": signal,
        "price": price,
        "tf": tf
    })

    save_memory(memory)

    # Simple memory-based adaptive decision: count recent wins/fails (simulated)
    last_signals = [m for m in memory if m["symbol"] == symbol and m["tf"] == tf]
    recent = last_signals[-10:]

    buy_count = sum(1 for s in recent if s["signal"] == "buy")
    sell_count = sum(1 for s in recent if s["signal"] == "sell")

    if signal == "buy" and buy_count >= 6:
        return "support"
    elif signal == "sell" and sell_count >= 6:
        return "support"
    elif buy_count + sell_count < 3:
        return "uncertain"
    else:
        return "reject"
