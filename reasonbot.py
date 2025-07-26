# filename: reasonbot.py
from typing import Dict, Any

def generate_reason(
    core_signal: str,
    pattern_data: Dict[str, str],
    risk_status: str,
    news_data: Dict[str, Any],
    confidence: float,
    market_structure: Dict[str, str],
    indicators: Dict[str, Any]
) -> str:
    """
    AI سے تیار کردہ تجارتی سگنلز کے لیے انسانی پڑھنے کے قابل وجہ تیار کرتا ہے۔
    """
    reason_parts = []
    signal_action = "خریدنے" if core_signal == "buy" else "بیچنے"
    
    # 1. بنیادی حکمت عملی کا خلاصہ
    reason_parts.append(f"بنیادی حکمت عملی {signal_action} کا موقع بتا رہی ہے کیونکہ متعدد اشارے موافق ہیں۔")
    
    # 2. انڈیکیٹرز کی تفصیل
    if indicators:
        rsi_val = indicators.get('rsi', 0)
        stoch_val = indicators.get('stoch_k', 0)
        if core_signal == "buy":
            reason_parts.append(f"EMA کراس اوور تیزی میں ہے، RSI ({rsi_val}) 50 سے اوپر ہے، اور Stochastic ({stoch_val}) اوور باٹ زون سے باہر ہے۔")
        else:
            reason_parts.append(f"EMA کراس اوور مندی میں ہے، RSI ({rsi_val}) 50 سے نیچے ہے، اور Stochastic ({stoch_val}) اوور سولڈ زون سے باہر ہے۔")

    # 3. مارکیٹ کی ساخت اور پیٹرن
    trend = market_structure.get("trend", "غیر متعین")
    if trend in ["اوپر کا رجحان", "نیچے کا رجحان"]:
        reason_parts.append(f"مارکیٹ کی مجموعی ساخت ({trend}) بھی اس سگنل کی حمایت کرتی ہے۔")
    
    pattern_name = pattern_data.get("pattern", "کوئی خاص پیٹرن نہیں")
    if pattern_data.get("type") in ["bullish", "bearish"]:
        reason_parts.append(f"ایک موافق کینڈل اسٹک پیٹرن ({pattern_name}) بھی دیکھا گیا ہے۔")

    # 4. رسک اور خبروں کا خلاصہ
    if risk_status == "Critical":
        reason_parts.append(f"**انتباہ: اعلیٰ اثر والی خبر ('{news_data.get('reason', '')[:50]}...') کی وجہ سے رسک انتہائی بلند (Critical) ہے۔**")
    elif risk_status == "High":
        reason_parts.append(f"**خبروں یا مارکیٹ کے اتار چڑھاؤ کی وجہ سے رسک بلند (High) ہے۔**")

    # 5. اعتماد کا خلاصہ
    if confidence < 60:
        reason_parts.append(f"کم اعتماد ({confidence:.1f}%) کی وجہ سے احتیاط برتیں۔")

    return " ".join(reason_parts)
    
