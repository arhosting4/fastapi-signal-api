# filename: reasonbot.py
from typing import Dict

def generate_reason(
    core_signal: str,
    pattern_data: Dict[str, str],
    risk_status: str,
    news_impact: str,
    confidence: float,
    market_structure: Dict[str, str]
) -> str:
    """
    AI سے تیار کردہ تجارتی سگنلز کے لیے انسانی پڑھنے کے قابل وجہ تیار کرتا ہے۔
    """
    reason_parts = []
    pattern_name = pattern_data.get("pattern", "کوئی خاص پیٹرن نہیں")
    pattern_type = pattern_data.get("type", "neutral")
    trend = market_structure.get("trend", "غیر متعین")

    # بنیادی حکمت عملی اور مارکیٹ کی ساخت
    if core_signal == "buy":
        reason_parts.append("بنیادی حکمت عملی خریدنے کا موقع بتا رہی ہے۔")
        if trend == "uptrend":
            reason_parts.append("مارکیٹ کی ساخت تیزی کے رجحان کی تصدیق کرتی ہے۔")
    elif core_signal == "sell":
        reason_parts.append("بنیادی حکمت عملی بیچنے کا موقع بتا رہی ہے۔")
        if trend == "downtrend":
            reason_parts.append("مارکیٹ کی ساخت مندی کے رجحان کی تصدیق کرتی ہے۔")

    # پیٹرن کی تصدیق
    if (core_signal == "buy" and pattern_type == "bullish") or \
       (core_signal == "sell" and pattern_type == "bearish"):
        reason_parts.append(f"ایک موافق پیٹرن ({pattern_name}) اس کی تصدیق کرتا ہے۔")
    elif pattern_type != "neutral":
        reason_parts.append(f"ایک مخالف پیٹرن ({pattern_name}) موجود ہے۔")

    # رسک اور خبریں
    if risk_status != "Normal":
        reason_parts.append(f"مارکیٹ کا رسک {risk_status.upper()} ہے۔")
    if news_impact != "Clear":
        reason_parts.append(f"اعلیٰ اثر والی خبروں کا امکان ہے۔")

    # اعتماد کا خلاصہ
    if confidence < 60:
        reason_parts.append(f"مجموعی اعتماد کم ہے ({confidence:.1f}%)۔")

    if not reason_parts:
        return "AI کا تجزیہ مکمل ہے۔ کوئی مضبوط اشارہ نہیں ملا۔"

    return " ".join(reason_parts)
    
