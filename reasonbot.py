# filename: reasonbot.py

from typing import Dict, Any

def generate_reason(
    symbol: str,
    tech_score: float,
    confidence: float,
    pattern: str,
    news: Dict[str, Any],
    structure: Dict[str, str],
    tp: float,
    sl: float
) -> str:
    """
    تمام تجزیاتی ماڈیولز سے حاصل کردہ ڈیٹا کی بنیاد پر ایک جامع اور انسانی فہم وجہ تیار کرتا ہے۔
    ★★★ تجزیہ میں شامل ہیں: تکنیکی اسکور، اعتماد، پیٹرن، خبریں، مارکیٹ اسٹرکچر، TP/SL ★★★
    """
    parts = []

    # 🔹 Symbol
    parts.append(f"یہ سگنل {symbol} پر مبنی ہے۔")

    # 🔹 Technical Score
    if tech_score >= 50:
        parts.append(f"تکنیکی اسکور {tech_score:.1f} ہے جو ایک مضبوط سگنل کی طرف اشارہ کرتا ہے۔")
    else:
        parts.append(f"تکنیکی اسکور {tech_score:.1f} قدرے کم ہے لیکن دیگر عوامل نے سگنل کو تقویت دی ہے۔")

    # 🔹 Confidence
    parts.append(f"ماڈل نے {confidence:.1f}% اعتماد کے ساتھ سگنل جاری کیا ہے۔")

    # 🔹 Pattern Recognition
    if pattern:
        parts.append(f"مارکیٹ میں '{pattern}' پیٹرن دیکھا گیا ہے، جو رجحان کی تصدیق کرتا ہے۔")

    # 🔹 News Impact
    if news and news.get("impact_score", 0) > 0:
        sentiment = news.get("sentiment", "N/A")
        parts.append(f"حالیہ خبروں کا اثر '{sentiment}' رہا ہے جس نے سگنل کو مزید مضبوط کیا۔")

    # 🔹 Market Structure
    if structure:
        trend = structure.get("trend", "نامعلوم")
        parts.append(f"مارکیٹ کا موجودہ رجحان '{trend}' پایا گیا ہے۔")

    # 🔹 TP/SL
    parts.append(f"منافع لینے کا ہدف (TP) {tp} اور نقصان روکنے کی حد (SL) {sl} مقرر کی گئی ہے۔")

    # 🔚 Final Join
    return " ".join(parts)
