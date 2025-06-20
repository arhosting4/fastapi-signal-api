import json
import os

FEEDBACK_FILE = "feedback_memory.json"

# Initialize memory file if not exist
if not os.path.exists(FEEDBACK_FILE):
    with open(FEEDBACK_FILE, "w") as f:
        json.dump({}, f)

def save_feedback(symbol, feedback):
    with open(FEEDBACK_FILE, "r") as f:
        data = json.load(f)

    if symbol not in data:
        data[symbol] = []

    data[symbol].append(feedback)

    with open(FEEDBACK_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_feedback_stats(symbol):
    with open(FEEDBACK_FILE, "r") as f:
        data = json.load(f)

    if symbol not in data or len(data[symbol]) == 0:
        return {"total": 0, "accuracy": None}

    total = len(data[symbol])
    correct = sum(1 for f in data[symbol] if f == "correct")
    accuracy = correct / total

    return {"total": total, "accuracy": round(accuracy * 100, 2)}
