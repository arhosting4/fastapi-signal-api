from typing import Dict, Any, List

def generate_reason(
    core_signal: str,
    pattern_data: Dict[str, str],
    risk_status: str,
    news_data: Dict[str, Any],
    confidence: float,
    market_structure: Dict[str, str],
    *,
    indicators: Dict[str, Any]
) -> str:
    """
    تمام تجزیاتی ماڈیولز سے حاصل کردہ ڈیٹا کی بنیاد پر ایک جامع اور انسانی فہم وجہ تیار کرتا ہے۔
    """
    reason_parts: List[str] = []
    signal_action = "خریداری" if core_signal == "buy" else "فروخت"
    
    # 1. بنیادی تکنیکی تجزیہ
    _add_technical_reason(reason_parts, signal_action, indicators)
    
    # 2. مارکیٹ کی ساخت اور پیٹرن کا تجزیہ
    _add_structure_and_pattern_reason(reason_parts, core_signal, market_structure, pattern_data)

    # 3. رسک اور خبروں کا انتباہ
    _add_risk_and_news_warning(reason_parts, risk_status, news_data)

    # 4. اعتماد کا خلاصہ
    if confidence < 75:
        reason_parts.append(f"کم اعتماد ({confidence:.1f}%) کی وجہ سے احتیاط کی سفارش کی جاتی ہے۔")

    return " ".join(reason_parts)

def _add_technical_reason(parts: List[str], action: str, indicators: Dict[str, Any]):
    """تکنیکی انڈیکیٹرز کی بنیاد پر وجہ کا حصہ تیار کرتا ہے۔"""
    tech_score = indicators.get('technical_score', 0)
    parts.append(f"مجموعی تکنیکی اسکور ({tech_score:.1f}) ایک مضبوط {action} کے رجحان کی نشاندہی کرتا ہے۔")
    
    # رفتار اور رجحان کا تجزیہ (Stochastic کے بغیر)
    rsi = indicators.get('rsi', 50)
    supertrend_dir = indicators.get('supertrend_direction', 'N/A')

    if action == "خریداری":
        if rsi > 50:
            parts.append("RSI تیزی کی رفتار (bullish momentum) دکھا رہا ہے۔")
        if supertrend_dir == "Up":
            parts.append("Supertrend نے اوپر کے رجحان (uptrend) کی تصدیق کی ہے۔")
    else:  # فروخت
        if rsi < 50:
            parts.append("RSI مندی کی رفتار (bearish momentum) دکھا رہا ہے۔")
        if supertrend_dir == "Down":
            parts.append("Supertrend نے نیچے کے رجحان (downtrend) کی تصدیق کی ہے۔")

def _add_structure_and_pattern_reason(
    parts: List[str], 
    signal: str, 
    structure: Dict[str, str], 
    pattern: Dict[str, str]
):
    """مارکیٹ کی ساخت اور کینڈل اسٹک پیٹرن کی بنیاد پر وجہ کا حصہ تیار کرتا ہے۔"""
    trend = structure.get("trend", "غیر متعین")
    if (signal == "buy" and trend == "اوپر کا رجحان") or \
       (signal == "sell" and trend == "نیچے کا رجحان"):
        parts.append(f"مارکیٹ کی مجموعی ساخت ({trend}) بھی اس سگنل کی حمایت کرتی ہے۔")
    
    pattern_name = pattern.get("pattern", "کوئی خاص پیٹرن نہیں")
    pattern_type = pattern.get("type", "neutral")
    if pattern_type != "neutral":
        parts.append(f"ایک موافق کینڈل اسٹک پیٹرن ({pattern_name}) بھی دیکھا گیا ہے۔")

def _add_risk_and_news_warning(
    parts: List[str], 
    risk: str, 
    news: Dict[str, Any]
):
    """رسک اور خبروں کی بنیاد پر انتباہی پیغامات شامل کرتا ہے۔"""
    news_reason = news.get('reason', '')
    if risk == "High" or risk == "Critical":
        warning = f"**انتباہ: مارکیٹ کا رسک بلند ('{risk}') ہے۔**"
        if "خبر" in news_reason:
            warning += f" وجہ: اعلیٰ اثر والی خبر ('{news_reason.split(': ')[-1][:50]}...')"
        parts.append(warning)
        
