# filename: supply_demand.py

import pandas as pd
from typing import List, Dict

def get_market_structure_analysis(candles: List[Dict], window: int = 10) -> Dict[str, str]:
    """
    مارکیٹ کی ساخت اور سپلائی/ڈیمانڈ زونز کا تجزیہ کرتا ہے۔
    """
    if len(candles) < window * 2:
        return {"trend": "غیر متعین", "zone": "غیر جانبدار", "reason": "ناکافی ڈیٹا۔"}

    # --- اہم تبدیلی: اب یہ پہلے سے ہی ڈکشنری ہے ---
    df = pd.DataFrame(candles)
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])

    df['swing_high'] = df['high'][(df['high'].shift(1) < df['high']) & (df['high'].shift(-1) < df['high'])]
    df['swing_low'] = df['low'][(df['low'].shift(1) > df['low']) & (df['low'].shift(-1) > df['low'])]

    recent_swings = df.tail(window * 2)
    recent_highs = recent_swings['swing_high'].dropna()
    recent_lows = recent_swings['swing_low'].dropna()

    if recent_highs.empty or recent_lows.empty:
        return {"trend": "رینجنگ", "zone": "غیر جانبدار", "reason": "کوئی واضح سوئنگ پوائنٹس نہیں"}

    last_high = recent_highs.iloc[-1]
    last_low = recent_lows.iloc[-1]
    last_close = df['close'].iloc[-1]

    dist_to_demand = abs(last_close - last_low)
    dist_to_supply = abs(last_close - last_high)

    zone_status = "غیر جانبدار"
    if dist_to_demand < dist_to_supply:
        zone_status = "ڈیمانڈ کے قریب"
    elif dist_to_supply < dist_to_demand:
        zone_status = "سپلائی کے قریب"

    trend = "رینجنگ"
    if len(recent_highs) >= 2 and len(recent_lows) >= 2:
        if recent_highs.iloc[-1] > recent_highs.iloc[-2] and recent_lows.iloc[-1] > recent_lows.iloc[-2]:
            trend = "اوپر کا رجحان"
        elif recent_highs.iloc[-1] < recent_highs.iloc[-2] and recent_lows.iloc[-1] < recent_lows.iloc[-2]:
            trend = "نیچے کا رجحان"

    return {"trend": trend, "zone": zone_status, "reason": f"قیمت {zone_status} ہے۔ موجودہ رجحان {trend} ہے۔"}
    
