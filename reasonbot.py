# filename: reasonbot.py

from typing import Dict, Any

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
    ★★★ اب یہ MACD اور Supertrend کو بھی شامل کرتا ہے۔ ★★★
    """
    reason_parts = []
    signal_action = "خریداری" if core_signal == "buy" else "فروخت"
    
    # 1. بنیادی تکنیکی اسکور
    tech_score = indicators.get('technical_score', 0)
    reason_parts.append(f"مجموعی تکنیکی اسکور ({tech_score:.1f}) ایک مضبوط {signal_action} کے رجحان کی نشاندہی کرتا ہے۔")
    
    # 2. رفتار اور رجحان کا تجزیہ (Momentum and Trend Analysis)
    macd_line = indicators.get('macd_line', 0)
    macd_signal_line = indicators.get('macd_signal_line', 0)
    supertrend_direction = indicators.get('supertrend_direction', 'N/A')

    if core_signal == "buy":
        if macd_line > macd_signal_line:
            reason_parts.append("MACD لائن سگنل لائن سے اوپر ہے، جو تیزی کی رفتار (bullish momentum) کو ظاہر کرتی ہے۔")
        if supertrend_direction == "Up":
            reason_parts.append("Supertrend نے اوپر کے رجحان (uptrend) کی تصدیق کی ہے۔")
    else:  # core_signal == "sell"
        if macd_line < macd_signal_line:
            reason_parts.append("MACD لائن سگنل لائن سے نیچے ہے، جو مندی کی رفتار (bearish momentum) کو ظاہر کرتی ہے۔")
        if supertrend_direction == "Down":
            reason_parts.append("Supertrend نے نیچے کے رجحان (downtrend) کی تصدیق کی ہے۔")

    # 3. مارکیٹ کی ساخت اور پیٹرن
    trend = market_structure.get("trend", "غیر متعین")
    if trend in ["اوپر کا رجحان", "نیچے کا رجحان"] and trend.startswith(core_signal.replace("buy", "اوپر").replace("sell", "نیچے")):
        reason_parts.append(f"مارکیٹ کی مجموعی ساخت ({trend}) بھی اس سگنل کی حمایت کرتی ہے۔")
    
    pattern_name = pattern_data.get("pattern", "کوئی خاص پیٹرن نہیں")
    if pattern_data.get("type") in ["bullish", "bearish"]:
        reason_parts.append(f"ایک موافق کینڈل اسٹک پیٹرن ({pattern_name}) بھی دیکھا گیا ہے۔")

    # 4. رسک اور خبروں کا انتباہ
    news_reason = news_data.get('reason', 'N/A')
    if risk_status == "Critical":
        reason_parts.append(f"**انتباہ: اعلیٰ اثر والی خبر ('{news_reason[:50]}...') کی وجہ سے رسک انتہائی بلند (Critical) ہے۔**")
    elif risk_status == "High":
        reason_parts.append(f"**خبروں یا مارکیٹ کے اتار چڑھاؤ کی وجہ سے رسک بلند (High) ہے۔**")

    # 5. اعتماد کا خلاصہ
    if confidence < 75:  # 70 کی حد کے قریب
        reason_parts.append(f"کم اعتماد ({confidence:.1f}%) کی وجہ سے احتیاط کی سفارش کی جاتی ہے۔")

    return " ".join(reason_parts)
    
