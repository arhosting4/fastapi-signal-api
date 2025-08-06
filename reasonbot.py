from typing import Dict, Any, List

def generate_reason(
    core_signal: str,
    pattern_data: Dict[str, str],
    news_data: Dict[str, Any],
    confidence: float,
    *,
    indicators: Dict[str, Any]
) -> str:
    """
    ایک سادہ اور واضح وجہ تیار کرتا ہے۔
    """
    reason_parts: List[str] = []
    signal_action = "خریداری" if core_signal == "buy" else "فروخت"
    
    # 1. بنیادی تکنیکی تجزیہ
    _add_technical_reason(reason_parts, signal_action, indicators)
    
    # 2. کینڈل اسٹک پیٹرن کا تجزیہ
    pattern_name = pattern_data.get("pattern", "کوئی خاص پیٹرن نہیں")
    pattern_type = pattern_data.get("type", "neutral")
    if pattern_type != "neutral" and pattern_type != "indecision":
        reason_parts.append(f"ایک موافق کینڈل اسٹک پیٹرن ({pattern_name}) بھی دیکھا گیا ہے۔")

    # 3. خبروں کا انتباہ
    news_reason = news_data.get('reason', '')
    if news_data.get('impact') == "High":
        reason_parts.append(f"**انتباہ: اعلیٰ اثر والی خبر ('{news_reason.split(': ')[-1][:50]}...') کی وجہ سے رسک بلند ہے۔**")

    # 4. اعتماد کا خلاصہ
    if confidence < 75:
        reason_parts.append(f"کم اعتماد ({confidence:.1f}%) کی وجہ سے احتیاط کی سفارش کی جاتی ہے۔")

    return " ".join(reason_parts)

def _add_technical_reason(parts: List[str], action: str, indicators: Dict[str, Any]):
    """
    تکنیکی انڈیکیٹرز کی بنیاد پر وجہ کا حصہ تیار کرتا ہے۔
    """
    tech_score = indicators.get('technical_score', 0)
    parts.append(f"مجموعی تکنیکی اسکور ({tech_score:.1f}) ایک مضبوط {action} کے رجحان کی نشاندہی کرتا ہے۔")
    
    supertrend_dir = indicators.get('supertrend_direction', 'N/A')

    if action == "خریداری" and supertrend_dir == "Up":
        parts.append("Supertrend نے اوپر کے رجحان (uptrend) کی تصدیق کی ہے۔")
    elif action == "فروخت" and supertrend_dir == "Down":
        parts.append("Supertrend نے نیچے کے رجحان (downtrend) کی تصدیق کی ہے۔")
                                                             
