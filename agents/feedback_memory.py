# src/agents/feedback_memory.py

feedback_log = []

def store_feedback(symbol: str, signal: str, outcome: str):
    """
    Stores feedback into memory for analysis or retraining.
    """
    entry = {
        "symbol": symbol,
        "signal": signal,
        "outcome": outcome
    }
    feedback_log.append(entry)
    print(f"[🧠 Feedback Stored] {entry}")
