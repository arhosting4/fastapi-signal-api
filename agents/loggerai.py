# src/agents/loggerai.py

import json
import os

LOG_FILE = "logs/signals_log.json"

def analyze_past_signals(symbol: str) -> dict:
    """
    Analyzes historical logs for a symbol to detect common success patterns.
    Returns learned insights like average confidence, signal trends, and tier bias.
    """
    if not os.path.exists(LOG_FILE):
        return {
            "average_confidence": 0,
            "most_common_tier": "Unknown",
            "most_common_signal": "Unknown",
            "total_logs": 0
        }

    try:
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)

        relevant = [log for log in logs if log.get("symbol") == symbol]

        if not relevant:
            return {
                "average_confidence": 0,
                "most_common_tier": "Unknown",
                "most_common_signal": "Unknown",
                "total_logs": 0
            }

        # Confidence averaging
        avg_conf = sum([log.get("confidence", 0) for log in relevant]) / len(relevant)

        # Most common tier and signal
        tiers = {}
        signals = {}
        for log in relevant:
            t = log.get("tier", "Unknown")
            s = log.get("signal", "Unknown")
            tiers[t] = tiers.get(t, 0) + 1
            signals[s] = signals.get(s, 0) + 1

        most_common_tier = max(tiers.items(), key=lambda x: x[1])[0]
        most_common_signal = max(signals.items(), key=lambda x: x[1])[0]

        return {
            "average_confidence": round(avg_conf, 2),
            "most_common_tier": most_common_tier,
            "most_common_signal": most_common_signal,
            "total_logs": len(relevant)
        }

    except Exception as e:
        print("⚠️ LoggerAI Error:", e)
        return {
            "average_confidence": 0,
            "most_common_tier": "Error",
            "most_common_signal": "Error",
            "total_logs": 0
        }
