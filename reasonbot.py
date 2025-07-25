# filename: reasonbot.py

from typing import Dict

def generate_reason(
    m15_trend: str,
    m5_signal_data: Dict,
    risk_status: str,
    news_impact: str,
    confidence: float
) -> str:
    """
    نئے ملٹی ٹائم فریم AI سگنل کے لیے انسانی پڑھنے کے قابل وجہ تیار کرتا ہے۔
    """
    reason_parts = []
    signal_type = m5_signal_data.get("signal")
    rsi_value = m5_signal_data.get("rsi", 50)

    # 1. بنیادی حکمت عملی کی وضاحت
    if signal_type == "buy":
        reason_parts.append(f"بڑا رجحان (M15) اوپر کی طرف ہے، اور M5 پر ایک خرید کا موقع ملا ہے۔")
    elif signal_type == "sell":
        reason_parts.append(f"بڑا رجحان (M15) نیچے کی طرف ہے، اور M5 پر ایک فروخت کا موقع ملا ہے۔")

    # 2. RSI کی تصدیق
    if (signal_type == "buy" and rsi_value > 55) or (signal_type == "sell" and rsi_value < 45):
        reason_parts.append(f"M5 پر رفتار (RSI: {rsi_value:.0f}) بھی اس کی تصدیق کر رہی ہے۔")
    else:
        reason_parts.append(f"تاہم، M5 پر رفتار (RSI: {rsi_value:.0f}) کمزور ہے۔")

    # 3. رسک اور خبروں کا خلاصہ
    if news_impact == "High":
        reason_parts.append("احتیاط: مارکیٹ میں زیادہ اثر والی خبروں کا امکان ہے۔")
    
    if risk_status == "High":
        reason_parts.append("مارکیٹ میں اس وقت اتار چڑھاؤ بہت زیادہ ہے۔")

    # 4. اعتماد کا حتمی بیان
    if confidence < 70:
        reason_parts.append(f"مجموعی طور پر، یہ ایک کمزور موقع ہے جس کا اعتماد اسکور {confidence:.1f}% ہے۔")

    if not reason_parts:
        return "AI کا تجزیہ مکمل ہے۔"

    return " ".join(reason_parts)
    
