# src/agents/trainerai.py

import json
import os
import random

LOG_FILE = "logs/signals_log.json"

def train_ai_memory(symbol: str) -> dict:
    """
    Simulates memory training by reviewing past logs.
    Rewards high-confidence signals with good tiers, penalizes noisy ones.
    """
    if not os.path.exists(LOG_FILE):
        return {
            "training_status": "No logs found",
            "memory_score": 0,
            "notes": "Need signal logs to begin memory training"
        }

    try:
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)

        filtered = [log for log in logs if log.get("symbol") == symbol]
        if not filtered:
            return {
                "training_status": "No symbol logs found",
                "memory_score": 0,
                "notes": f"No entries found for {symbol}"
            }

        score = 0
        notes = []

        for log in filtered:
            conf = log.get("confidence", 0)
            tier = log.get("tier", "")
            signal = log.get("signal", "")

            # Reward logic
            if conf > 80 and tier.startswith("Tier 1"):
                score += 3
                notes.append(f"✅ High confidence Tier 1: {signal}")
            elif conf > 70 and "Tier 2" in tier:
                score += 2
            elif "Tier 4" in tier:
                score -= 2
                notes.append(f"⚠️ Weak signal flagged in Tier 4")

        memory_score = max(0, min(100, int((score / len(filtered)) * 10 + random.uniform(0, 5))))

        return {
            "training_status": "Memory trained",
            "memory_score": memory_score,
            "notes": notes[-5:]
        }

    except Exception as e:
        return {
            "training_status": "Error",
            "memory_score": 0,
            "notes": [str(e)]
        }
