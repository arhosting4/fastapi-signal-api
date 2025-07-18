import json
import os

FEEDBACK_FILE = "data/feedback_memory.json"
os.makedirs("data", exist_ok=True)

# یقینی بنائیں کہ فائل موجود ہے
if not os.path.exists(FEEDBACK_FILE):
    try:
        with open(FEEDBACK_FILE, "w") as f:
            json.dump({}, f)
        print(f"✅ Created empty feedback memory file: {FEEDBACK_FILE}")
    except Exception as e:
        print(f"⚠️ Error creating feedback memory file: {e}")

def save_feedback(performance_key: str, feedback: str):
    """
    ایک مخصوص پرفارمنس کی (مثلاً 'XAU/USD_15m') کے لیے فیڈ بیک محفوظ کرتا ہے۔
    """
    try:
        with open(FEEDBACK_FILE, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        data = {}
        print(f"⚠️ Feedback file was empty or corrupted, re-initializing.")

    if performance_key not in data:
        data[performance_key] = []

    data[performance_key].append(feedback)

    try:
        with open(FEEDBACK_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Feedback saved for '{performance_key}': {feedback}")
    except Exception as e:
        print(f"⚠️ Error saving feedback: {e}")

def get_feedback_stats(performance_key: str) -> dict:
    """
    ایک مخصوص پرفارمنس کی کے لیے فیڈ بیک کے اعداد و شمار حاصل کرتا ہے۔
    """
    try:
        with open(FEEDBACK_FILE, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"total": 0, "accuracy": None, "correct": 0, "incorrect": 0}

    if performance_key not in data or not data[performance_key]:
        return {"total": 0, "accuracy": None, "correct": 0, "incorrect": 0}

    feedback_list = data[performance_key]
    total = len(feedback_list)
    correct = feedback_list.count("correct")
    incorrect = feedback_list.count("incorrect")
    
    # صرف 'correct' اور 'incorrect' کی بنیاد پر ایکوریسی کیلکولیٹ کریں
    relevant_trades = correct + incorrect
    accuracy = (correct / relevant_trades) * 100 if relevant_trades > 0 else 0

    return {
        "total": total,
        "correct": correct,
        "incorrect": incorrect,
        "accuracy": round(accuracy, 2)
    }
    
