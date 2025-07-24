# filename: supply_demand.py
import pandas as pd
from typing import List, Dict

from schemas import Candle

def get_market_structure_analysis(candles: List[Candle], window: int = 20) -> Dict[str, str]:
    """
    کینڈلز کی بنیاد پر مارکیٹ کی ساخت (رجحان) اور سپلائی/ڈیمانڈ زونز کا تجزیہ کرتا ہے۔
    """
    if len(candles) < window:
        return {"trend": "undetermined", "zone": "neutral", "reason": "ساخت کے تجزیے کے لیے ناکافی ڈیٹا۔"}

    df = pd.DataFrame([c.dict() for c in candles])

    # سوئنگ ہائی اور لو کی شناخت کریں
    df['swing_high'] = df['high'][(df['high'].shift(1) < df['high']) & (df['high'].shift(-1) < df['high'])]
    df['swing_low'] = df['low'][(df['low'].shift(1) > df['low']) & (df['low'].shift(-1) > df['low'])]

    recent_swings = df.tail(window)
    recent_highs = recent_swings['swing_high'].dropna()
    recent_lows = recent_swings['swing_low'].dropna()

    if len(recent_highs) < 2 or len(recent_lows) < 2:
        return {"trend": "ranging", "zone": "neutral", "reason": "حال ہی میں کوئی واضح سوئنگ پوائنٹس نہیں۔"}

    # ٹرینڈ کی شناخت (اعلیٰ ہائی، اعلیٰ لو)
    trend = "ranging"
    if recent_highs.iloc[-1] > recent_highs.iloc[-2] and recent_lows.iloc[-1] > recent_lows.iloc[-2]:
        trend = "uptrend"
    elif recent_highs.iloc[-1] < recent_highs.iloc[-2] and recent_lows.iloc[-1] < recent_lows.iloc[-2]:
        trend = "downtrend"

    # زون کا تجزیہ
    last_high = recent_highs.iloc[-1]
    last_low = recent_lows.iloc[-1]
    last_close = df['close'].iloc[-1]

    dist_to_demand = abs(last_close - last_low)
    dist_to_supply = abs(last_close - last_high)

    zone_status = "neutral"
    if dist_to_demand < dist_to_supply:
        zone_status = "near_demand"
    elif dist_to_supply < dist_to_demand:
        zone_status = "near_supply"

    return {"trend": trend, "zone": zone_status, "reason": f"قیمت {zone_status} ہے۔ موجودہ رجحان {trend} ہے۔"}
    
