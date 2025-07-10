import random
from feedback_memory import get_feedback_stats # get_feedback_stats کو امپورٹ کریں

def get_confidence(
    symbol: str, # نیا پیرامیٹر: سمبل
    core_signal: str,
    pattern_signal_type: str, # bullish, bearish, neutral
    risk_status: str, # Normal, Moderate, High
    news_impact: str # Clear, Low, Medium, High
) -> float:
    """
    Estimates signal confidence based on current logic fusion.
    This version considers alignment, risk, news, and historical feedback.
    """
    confidence = 50.0 # Base confidence

    # --- 1. Core Signal and Pattern Alignment ---
    if core_signal == "buy" and pattern_signal_type == "bullish":
        confidence += 20
    elif core_signal == "sell" and pattern_signal_type == "bearish":
        confidence += 20
    elif core_signal == "wait" and pattern_signal_type == "neutral":
        confidence += 10
    elif (core_signal == "buy" and pattern_signal_type == "bearish") or \
         (core_signal == "sell" and pattern_signal_type == "bullish"):
        confidence -= 25 # Strong contradiction

    # --- 2. Risk Assessment Impact ---
    if risk_status == "High":
        confidence -= 20
    elif risk_status == "Moderate":
        confidence -= 10

    # --- 3. News Impact Assessment ---
    if news_impact == "High":
        confidence -= 25
    elif news_impact == "Medium":
        confidence -= 15
    elif news_impact == "Low":
        confidence -= 5

    # --- 4. Feedback-Based Adjustment (The new logic) ---
    feedback_stats = get_feedback_stats(symbol)
    accuracy = feedback_stats.get("accuracy")
    total_feedback = feedback_stats.get("total")

    # Only adjust if we have a meaningful amount of feedback (e.g., more than 5 data points)
    if accuracy is not None and total_feedback > 5:
        if accuracy > 75: # High accuracy
            confidence += 10
            print(f"Feedback Adjustment: +10 confidence for {symbol} due to high accuracy ({accuracy}%)")
        elif accuracy > 60: # Good accuracy
            confidence += 5
            print(f"Feedback Adjustment: +5 confidence for {symbol} due to good accuracy ({accuracy}%)")
        elif accuracy < 40: # Poor accuracy
            confidence -= 10
            print(f"Feedback Adjustment: -10 confidence for {symbol} due to poor accuracy ({accuracy}%)")

    # --- 5. Additional Factors ---
    if core_signal == "wait":
        confidence -= 10

    # Ensure confidence stays within 0-100 range
    confidence = max(0.0, min(100.0, confidence))

    # Add a small random variation
    confidence += random.uniform(-2.0, 2.0)
    confidence = max(0.0, min(100.0, confidence))

    return round(confidence, 2)
    
