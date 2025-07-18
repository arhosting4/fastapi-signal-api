import pandas as pd
from typing import List, Dict, Tuple

def find_support_resistance(candles: List[Dict]) -> Tuple[List[float], List[float]]:
    """
    کینڈل ڈیٹا سے اہم سپورٹ اور ریزسٹنس لیولز کی شناخت کرتا ہے۔
    
    Parameters:
        candles (list): OHLC کینڈلز کی فہرست۔

    Returns:
        tuple: (سپورٹ لیولز کی فہرست, ریزسٹنس لیولز کی فہرست)
    """
    if len(candles) < 20:
        return [], []

    df = pd.DataFrame(candles)
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])

    support_levels = []
    resistance_levels = []

    # لیولز کی شناخت کے لیے ایک سادہ لیکن مؤثر طریقہ
    # ہم ان چوٹیوں (peaks) اور گہرائیوں (troughs) کو تلاش کریں گے جو اپنے پڑوسیوں سے نمایاں ہوں
    for i in range(5, len(df) - 5):
        # ریزسٹنس (چوٹی) کی شرط
        is_resistance = True
        for j in range(1, 6):
            if df['high'][i] < df['high'][i-j] or df['high'][i] < df['high'][i+j]:
                is_resistance = False
                break
        if is_resistance:
            resistance_levels.append(df['high'][i])

        # سپورٹ (گہرائی) کی شرط
        is_support = True
        for j in range(1, 6):
            if df['low'][i] > df['low'][i-j] or df['low'][i] > df['low'][i+j]:
                is_support = False
                break
        if is_support:
            support_levels.append(df['low'][i])

    # لیولز کو قریب ترین ویلیوز کو ملا کر صاف کریں
    # (یہ ایک جدید قدم ہے جسے ہم بعد میں شامل کر سکتے ہیں)
    
    # صرف آخری 5 منفرد لیولز واپس کریں تاکہ بہت زیادہ شور نہ ہو
    unique_supports = sorted(list(set(support_levels)), reverse=True)[:5]
    unique_resistances = sorted(list(set(resistance_levels)), reverse=True)[:5]

    return unique_supports, unique_resistances

def analyze_market_structure(signal: str, current_price: float, candles: List[Dict]) -> Dict:
    """
    موجودہ سگنل کا سپورٹ اور ریزسٹنس کے حوالے سے تجزیہ کرتا ہے۔
    """
    supports, resistances = find_support_resistance(candles)
    
    analysis = {
        "decision": "proceed", # 'proceed' یا 'block'
        "reason": "Market structure appears favorable.",
        "confidence_boost": 0.0
    }

    if not supports and not resistances:
        return analysis # اگر کوئی لیول نہیں ملا تو کچھ نہ کریں

    if signal == "buy":
        # قریب ترین ریزسٹنس تلاش کریں
        nearest_resistance = min([r for r in resistances if r > current_price], default=None)
        if nearest_resistance:
            # اگر ریزسٹنس بہت قریب ہے (قیمت کے 1% کے اندر) تو سگنل کو بلاک کر دیں
            if (nearest_resistance - current_price) / current_price < 0.005: # 0.5% کا فاصلہ
                analysis["decision"] = "block"
                analysis["reason"] = f"Signal blocked by strong resistance level very close at {nearest_resistance:.5f}."
                return analysis

        # قریب ترین سپورٹ تلاش کریں
        nearest_support = max([s for s in supports if s < current_price], default=None)
        if nearest_support:
            # اگر قیمت سپورٹ سے باؤنس ہوئی ہے تو اعتماد بڑھائیں
            if (current_price - nearest_support) / current_price < 0.003: # 0.3% کا فاصلہ
                analysis["reason"] = "Signal is bouncing off a nearby support level."
                analysis["confidence_boost"] = 5.0 # 5 پوائنٹس کا اضافہ

    elif signal == "sell":
        # قریب ترین سپورٹ تلاش کریں
        nearest_support = max([s for s in supports if s < current_price], default=None)
        if nearest_support:
            if (current_price - nearest_support) / current_price < 0.005: # 0.5% کا فاصلہ
                analysis["decision"] = "block"
                analysis["reason"] = f"Signal blocked by strong support level very close at {nearest_support:.5f}."
                return analysis

        # قریب ترین ریزسٹنس تلاش کریں
        nearest_resistance = min([r for r in resistances if r > current_price], default=None)
        if nearest_resistance:
            if (nearest_resistance - current_price) / current_price < 0.003: # 0.3% کا فاصلہ
                analysis["reason"] = "Signal is rejecting from a nearby resistance level."
                analysis["confidence_boost"] = 5.0 # 5 پوائنٹس کا اضافہ

    return analysis
                
