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
    reason_parts = []
    signal_action = "خریدنے" if core_signal == "buy" else "بیچنے"
    
    # 1. بنیادی حکمت عملی کا خلاصہ
    tech_score = indicators.get('technical_score', 0)
    reason_parts.append(f"بنیادی تکنیکی تجزیے نے {tech_score:.1f} کا {signal_action} کا اسکور دیا ہے۔")
    
    # 2. انڈیکیٹرز کی تفصیل
    rsi_val = indicators.get('rsi', 0)
    stoch_val = indicators.get('stoch_k', 0)
    if core_signal == "buy":
        reason_parts.append(f"اہم اشارے جیسے EMA کراس اوور، RSI ({rsi_val:.1f}) اور Stochastic ({stoch_val:.1f}) زیادہ تر تیزی کے حق میں ہیں۔")
    else:
        reason_parts.append(f"اہم اشارے جیسے EMA کراس اوور، RSI ({rsi_val:.1f}) اور Stochastic ({stoch_val:.1f}) زیادہ تر مندی کے حق میں ہیں۔")

    # 3. مارکیٹ کی ساخت اور پیٹرن
    trend = market_structure.get("trend", "غیر متعین")
    if trend in ["اوپر کا رجحان", "نیچے کا رجحان"]:
        reason_parts.append(f"مارکیٹ کی مجموعی ساخت ({trend}) بھی اس سگنل کی حمایت کرتی ہے۔")
    
    pattern_name = pattern_data.get("pattern", "کوئی خاص پیٹرن نہیں")
    if pattern_data.get("type") in ["bullish", "bearish"]:
        reason_parts.append(f"ایک موافق کینڈل اسٹک پیٹرن ({pattern_name}) بھی دیکھا گیا ہے۔")

    # 4. رسک اور خبروں کا خلاصہ
    news_reason = news_data.get('reason', 'N/A')
    if risk_status == "Critical":
        reason_parts.append(f"**انتباہ: اعلیٰ اثر والی خبر ('{news_reason[:50]}...') کی وجہ سے رسک انتہائی بلند (Critical) ہے۔**")
    elif risk_status == "High":
        reason_parts.append(f"**خبروں یا مارکیٹ کے اتار چڑھاؤ کی وجہ سے رسک بلند (High) ہے۔**")

    # 5. اعتماد کا خلاصہ
    if confidence < 65:
        reason_parts.append(f"کم اعتماد ({confidence:.1f}%) کی وجہ سے احتیاط کی سفارش کی جاتی ہے۔")

    return " ".join(reason_parts)
    
