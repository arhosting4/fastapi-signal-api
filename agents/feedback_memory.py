# src/agents/feedback_memory.py

import json
import os

FEEDBACK_FILE = "feedback_memory.json"
FEEDBACK_DIR = "data" # Directory to store feedback data

# Ensure the feedback directory exists
os.makedirs(FEEDBACK_DIR, exist_ok=True)
FEEDBACK_FILE_PATH = os.path.join(FEEDBACK_DIR, FEEDBACK_FILE)

# Initialize memory file if not exist
if not os.path.exists(FEEDBACK_FILE_PATH):
    try:
        with open(FEEDBACK_FILE_PATH, "w") as f:
            json.dump({}, f)
        print(f"✅ Created empty feedback memory file: {FEEDBACK_FILE_PATH}")
    except Exception as e:
        print(f"⚠️ Error creating feedback memory file: {e}")

def save_feedback(symbol: str, feedback: str):
    """
    Saves feedback for a given symbol.

    Parameters:
        symbol (str): The trading pair symbol.
        feedback (str): The feedback string (e.g., "correct", "incorrect", "missed").
    """
    try:
        with open(FEEDBACK_FILE_PATH, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        # Handle case where file might be empty or corrupted
        data = {}
        print(f"⚠️ Feedback file {FEEDBACK_FILE_PATH} was empty or corrupted, re-initializing.")
    except FileNotFoundError:
        data = {} # Should not happen if os.makedirs and initial dump worked
        print(f"⚠️ Feedback file {FEEDBACK_FILE_PATH} not found, re-initializing.")

    if symbol not in data:
        data[symbol] = []

    data[symbol].append(feedback)

    try:
        with open(FEEDBACK_FILE_PATH, "w") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Feedback saved for {symbol}: {feedback}")
    except Exception as e:
        print(f"⚠️ Error saving feedback: {e}")

def get_feedback_stats(symbol: str) -> dict:
    """
    Retrieves feedback statistics for a given symbol.

    Parameters:
        symbol (str): The trading pair symbol.

    Returns:
        dict: Statistics including total feedback and accuracy.
    """
    try:
        with open(FEEDBACK_FILE_PATH, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"total": 0, "accuracy": None, "correct": 0, "incorrect": 0, "missed": 0}

    if symbol not in data or len(data[symbol]) == 0:
        return {"total": 0, "accuracy": None, "correct": 0, "incorrect": 0, "missed": 0}

    total = len(data[symbol])
    correct = sum(1 for f in data[symbol] if f == "correct")
    incorrect = sum(1 for f in data[symbol] if f == "incorrect")
    missed = sum(1 for f in data[symbol] if f == "missed") # Assuming 'missed' is another feedback type

    accuracy = (correct / total) * 100 if total > 0 else None

    return {
        "total": total,
        "correct": correct,
        "incorrect": incorrect,
        "missed": missed,
        "accuracy": round(accuracy, 2) if accuracy is not None else None
    }

