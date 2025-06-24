# src/agents/trainerai.py

import json
from datetime import datetime
import os

LOG_FILE = "learning_memory.json"

def update_learning_memory(symbol: str, signal: str, candle_pattern: str, risk_level: str, context_reason: str):
    """
    Logs the learning memory for future analysis.
    """

    memory = {
        "timestamp": datetime.utcnow().isoformat(),
        "symbol": symbol,
        "signal": signal,
        "pattern": candle_pattern,
        "risk": risk_level,
        "reasoning": context_reason
    }

    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                data = json.load(f)
        else:
            data = []

        data.append(memory)

        with open(LOG_FILE, "w") as f:
            json.dump(data, f, indent=4)

    except Exception as e:
        print(f"[TrainerAI] Memory update failed: {e}")
