import random
from feedback_memory import get_feedback_stats

def get_confidence(
    core_signal: str,
    pattern_signal_type: str,
    risk_status: str,
    news_impact: str,
    symbol: str
) -> float:
    """
    Estimates signal confidence based on current logic fusion.
    """
    # --- اہم تبدیلی: بنیادی اعتماد کو تھوڑا بڑھائیں ---
    confidence = 55.0  # پہلے 50.0 تھا

    # 1. Core Signal and Pattern Alignment
    if core_signal == "buy" and pattern_signal_type == "bullish":
        confidence += 20
    elif core_signal == "sell" and pattern_signal_type == "bearish":
        confidence += 20
    elif core_signal == "wait" and pattern_signal_type == "neutral":
        confidence += 5 # پہلے 10 تھا
    elif (core_signal == "buy" and pattern_signal_type == "bearish") or \
         (core_signal == "sell" and pattern_signal_type == "bullish"):
        confidence -= 25

    # 2. Risk Assessment Impact
    if risk_status == "High":
        confidence -= 20
    elif risk_status == "Moderate":
        confidence -= 5 # پہلے 10 تھا

    # 3. News Impact Assessment
    if news_impact == "High":
        confidence -= 20 # پہلے 25 تھا
    elif news_impact == "Medium":
        confidence -= 10 # پہلے 15 تھا
    elif news_impact == "Low":
        confidence -= 3 # پہلے 5 تھا

    # 4. Feedback Loop Impact
    feedback = get_feedback_stats(symbol)
    if feedback and feedback["total"] > 10: # کم از کم 10 فیڈ بیک کے بعد
        accuracy = feedback.get("accuracy", 50) # اگر accuracy نہ ہو تو 50 مانیں
        if accuracy > 70:
            confidence += 10 # اگر AI اچھا کام کر رہا ہے تو اعتماد بڑھائیں
        elif accuracy < 40:
            confidence -= 15 # اگر برا کام کر رہا ہے تو اعتماد کم کریں

    # --- اہم تبدیلی: wait سگنل پر جرمانہ ہٹا دیں ---
    # if core_signal == "wait":
    #     confidence -= 10 # اس لائن کو ہٹا دیا گیا ہے

    # Ensure confidence stays within 0-100 range
    confidence = max(0.0, min(100.0, confidence))
    confidence += random.uniform(-2.0, 2.0)
    confidence = max(0.0, min(100.0, confidence))

    return round(confidence, 2)
