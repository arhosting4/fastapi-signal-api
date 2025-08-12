# filename: reasonbot.py

from typing import Dict, Any, List

def generate_reason(
    core_signal: str,
    pattern_data: Dict[str, str],
    news_data: Dict[str, Any],
    confidence: float,
    strategy_type: str,
    market_regime: str,
    signal_grade: str # نیا پیرامیٹر
) -> str:
    """
    تمام تجزیاتی ماڈیولز سے حاصل کردہ ڈیٹا کی بنیاد پر ایک جامع وجہ تیار کرتا ہے۔
    یہ اب سگنل کے گریڈ کو بھی شامل کرتا ہے۔
    """
    reason_parts: List[str] = []
    signal_action = "خریداری" if core_signal == "buy" else "فروخت"
    
    # === پروجیکٹ ویلوسیٹی اپ ڈیٹ ===
    # وجہ کا آغاز سگنل کے گریڈ اور حکمت عملی سے کریں
    reason_parts.append(f"**{signal_grade} سگنل:** مارکیٹ کا نظام '{market_regime}' ہے۔")
    
    if strategy_type == "Trend-Following":
        reason_parts.append(f"ہماری ٹرینڈ فالوونگ حکمت عملی نے ایک {signal_action} کا موقع شناخت کیا ہے۔")
    elif strategy_type == "Range-Reversal":
        reason_parts.append(f"ہماری ریورسل حکمت عملی نے ایک ممکنہ {signal_action} کا موقع شناخت کیا ہے۔")

    # اضافی تصدیق کی تفصیلات
    if signal_grade == "A-Grade":
        reason_parts.append("اس سگنل کی একাধিক ذرائع سے تصدیق ہوئی ہے، جس سے اس کا اعتماد بڑھ گیا ہے۔")
    else: # B-Grade
        reason_parts.append("یہ ایک بنیادی رفتار کا سگنل ہے۔ تیز منافع کے لیے 1:1.5 کا RR استعمال کیا جا رہا ہے۔")

    # خبروں کا انتباہ
    if news_data.get("impact") == "High":
        reason_parts.append("**انتباہ: ایک اعلیٰ اثر والی خبر قریب ہے، جس سے رسک بڑھ سکتا ہے۔**")

    return " ".join(reason_parts)
    
