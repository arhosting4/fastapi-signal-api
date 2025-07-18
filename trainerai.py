import random
from feedback_memory import get_feedback_stats # فیڈ بیک حاصل کرنے کے لیے امپورٹ کریں

def get_confidence(
    core_signal: str,
    pattern_signal_type: str,
    risk_status: str,
    news_impact: str,
    symbol: str,
    timeframe: str # --- نیا: ٹائم فریم بھی شامل کریں ---
) -> float:
    """
    سگنل کے اعتماد کا تخمینہ لگاتا ہے، اب ماضی کی کارکردگی کو بھی مدنظر رکھتے ہوئے۔
    """
    base_confidence = 55.0

    # 1. تکنیکی عوامل (پہلے کی طرح)
    if core_signal == "buy" and pattern_signal_type == "bullish":
        base_confidence += 15
    elif core_signal == "sell" and pattern_signal_type == "bearish":
        base_confidence += 15
    elif (core_signal == "buy" and pattern_signal_type == "bearish") or \
         (core_signal == "sell" and pattern_signal_type == "bullish"):
        base_confidence -= 20

    if risk_status == "High":
        base_confidence -= 15
    elif risk_status == "Moderate":
        base_confidence -= 7

    if news_impact == "High":
        base_confidence -= 20
    elif news_impact == "Medium":
        base_confidence -= 10

    # --- 2. نیا اور اہم مرحلہ: فیڈ بیک لوپ ---
    # ہم ایک منفرد شناخت کنندہ بنائیں گے، جیسے "XAU/USD_15m"
    performance_key = f"{symbol}_{timeframe}"
    stats = get_feedback_stats(performance_key)

    if stats and stats["total"] >= 5: # کم از کم 5 ٹریڈز کے بعد سیکھنا شروع کریں
        accuracy = stats.get("accuracy", 50.0) # اگر accuracy نہ ہو تو 50 مانیں
        
        print(f"Feedback Loop for {performance_key}: Accuracy is {accuracy}% over {stats['total']} trades.")

        if accuracy > 75:
            # بہت اچھی کارکردگی -> اعتماد میں بڑا اضافہ
            base_confidence += 10
            print(f"Applying +10 confidence boost for high accuracy.")
        elif accuracy > 60:
            # اچھی کارکردگی -> تھوڑا اضافہ
            base_confidence += 5
            print(f"Applying +5 confidence boost for good accuracy.")
        elif accuracy < 40:
            # بری کارکردگی -> اعتماد میں کمی
            base_confidence -= 10
            print(f"Applying -10 confidence penalty for low accuracy.")
        elif accuracy < 25:
            # بہت بری کارکردگی -> اعتماد میں بڑی کمی
            base_confidence -= 15
            print(f"Applying -15 confidence penalty for very low accuracy.")
    
    # اعتماد کو 0-100 کی حد میں رکھیں
    final_confidence = max(0.0, min(100.0, base_confidence))
    
    # تھوڑا سا بے ترتیب عنصر شامل کریں تاکہ ہر بار ایک جیسی ویلیو نہ آئے
    final_confidence += random.uniform(-1.5, 1.5)
    final_confidence = max(0.0, min(100.0, final_confidence))

    return round(final_confidence, 2)
    
