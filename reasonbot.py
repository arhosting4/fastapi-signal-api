# filename: reasonbot.py

from typing import Dict, Any, List

def generate_reason(
    core_signal: str,
    pattern_data: Dict[str, str],
    news_data: Dict[str, Any],
    confidence: float,
    strategy_type: str,
    market_regime: str
) -> str:
    """
    تمام تجزیاتی ماڈیولز سے حاصل کردہ ڈیٹا کی بنیاد پر ایک جامع اور انسانی فہم وجہ تیار کرتا ہے۔
    یہ اب حکمت عملی کی قسم اور مارکیٹ کے نظام کو بھی شامل کرتا ہے۔
    """
    reason_parts: List[str] = []
    signal_action = "خریداری" if core_signal == "buy" else "فروخت"
    
    # 1. بنیادی حکمت عملی کی وجہ
    if strategy_type == "Trend-Following":
        reason_parts.append(f"مارکیٹ کا نظام '{market_regime}' ایک مضبوط رجحان کی نشاندہی کرتا ہے۔")
        reason_parts.append(f"ہماری ٹرینڈ فالوونگ حکمت عملی نے ایک {signal_action} کا موقع شناخت کیا ہے۔")
    elif strategy_type == "Range-Reversal":
        reason_parts.append(f"مارکیٹ کا نظام '{market_regime}' ہے۔ قیمت بولنگر بینڈ کی حد تک پہنچ گئی ہے۔")
        reason_parts.append(f"ہماری ریورسل حکمت عملی نے ایک ممکنہ {signal_action} کا موقع شناخت کیا ہے۔")

    # 2. اضافی تصدیق (کینڈل اسٹک پیٹرن)
    pattern_name = pattern_data.get("pattern", "کوئی خاص پیٹرن نہیں")
    pattern_type = pattern_data.get("type", "neutral")
    if (core_signal == "buy" and pattern_type == "bullish") or \
       (core_signal == "sell" and pattern_type == "bearish"):
        reason_parts.append(f"ایک موافق کینڈل اسٹک پیٹرن ({pattern_name}) نے اس سگنل کی مزید تصدیق کی ہے۔")

    # 3. خبروں کا انتباہ
    if news_data.get("impact") == "High":
        reason_parts.append("**انتباہ: ایک اعلیٰ اثر والی خبر قریب ہے، جس سے رسک بڑھ سکتا ہے۔**")

    # 4. اعتماد کا خلاصہ
    if confidence < 75:
        reason_parts.append(f"کم اعتماد ({confidence:.1f}%) کی وجہ سے احتیاط کی سفارش کی جاتی ہے۔")

    return " ".join(reason_parts)
        
