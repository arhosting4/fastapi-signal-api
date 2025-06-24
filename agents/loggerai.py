# src/agents/loggerai.py

import datetime
import json

def log_ai_decision(signal: str, reason: str, price: float):
    """
    Logs the AI signal decision with reason and price to a local file or stdout.
    """

    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "signal": signal,
        "price": price,
        "reason": reason
    }

    # Print log for Render logs
    print(f"[AI Decision] {json.dumps(log_entry)}")

    # Optionally, write to file (uncomment if local logging is needed)
    # with open("ai_decisions.log", "a") as log_file:
    #     log_file.write(json.dumps(log_entry) + "\n")
