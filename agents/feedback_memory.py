# src/agents/feedback_memory.py

feedback_store = {}

def update_feedback(symbol: str, signal: str, success: bool):
    """
    Store feedback on whether the signal was successful or not.
    """
    key = f"{symbol}:{signal}"
    if key not in feedback_store:
        feedback_store[key] = {"total": 0, "success": 0}

    feedback_store[key]["total"] += 1
    if success:
        feedback_store[key]["success"] += 1

def get_feedback_accuracy(symbol: str, signal: str) -> float:
    """
    Returns the success rate of a signal for a symbol.
    """
    key = f"{symbol}:{signal}"
    record = feedback_store.get(key, {"total": 0, "success": 0})

    if record["total"] == 0:
        return 0.0

    return record["success"] / record["total"]
