# src/agents/trainerai.py

from .feedback_memory import get_feedback_accuracy

def auto_tune_confidence(base_confidence: float, symbol: str, signal: str) -> float:
    """
    Adjust the confidence score based on past performance.
    """
    try:
        historical_accuracy = get_feedback_accuracy(symbol, signal)
        # Blend current and historical score
        tuned_confidence = (0.7 * base_confidence) + (0.3 * historical_accuracy)
        return round(tuned_confidence, 4)
    except Exception:
        return base_confidence
