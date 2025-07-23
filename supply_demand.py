# supply_demand.py

import pandas as pd

def get_market_structure_analysis(candles: list, window: int = 10) -> dict:
    """
    کینڈلز کی بنیاد پر مارکیٹ کی ساخت (ٹرینڈ) اور سپلائی/ڈیمانڈ زونز کا تجزیہ کرتا ہے۔
    """
    if len(candles) < window * 2:
        return {"trend": "undetermined", "zone": "neutral", "reason": "Insufficient data for structure analysis."}

    df = pd.DataFrame(candles)
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])

    # سوئنگ ہائی اور لو کی شناخت کریں
    df['swing_high'] = df['high'][(df['high'].shift(1) < df['high']) & (df['high'].shift(-1) < df['high'])]
    df['swing_low'] = df['low'][(df['low'].shift(1) > df['low']) & (df['low'].shift(-1) > df['low'])]

    recent_swings = df.tail(window * 2)
    recent_highs = recent_swings['swing_high'].dropna()
    recent_lows = recent_swings['swing_low'].dropna()

    if recent_highs.empty or recent_lows.empty:
        return {"trend": "ranging", "zone": "neutral", "reason": "No clear swing points recently."}

    last_high = recent_highs.iloc[-1]  # تازہ ترین سپلائی زون
    last_low = recent_lows.iloc[-1]    # تازہ ترین ڈیمانڈ زون
    last_close = df['close'].iloc[-1]

    # قیمت کا زون سے فاصلہ
    dist_to_demand = abs(last_close - last_low)
    dist_to_supply = abs(last_close - last_high)

    zone_status = "neutral"
    if dist_to_demand < dist_to_supply:
        zone_status = "near_demand"
    elif dist_to_supply < dist_to_demand:
        zone_status = "near_supply"

    # ٹرینڈ کی شناخت
    trend = "ranging"
    if len(recent_highs) >= 2 and len(recent_lows) >= 2:
        if recent_highs.iloc[-1] > recent_highs.iloc[-2] and recent_lows.iloc[-1] > recent_lows.iloc[-2]:
            trend = "uptrend"
        elif recent_highs.iloc[-1] < recent_highs.iloc[-2] and recent_lows.iloc[-1] < recent_lows.iloc[-2]:
            trend = "downtrend"

    return {"trend": trend, "zone": zone_status, "reason": f"Price is {zone_status}. Current trend is {trend}."}
