import pandas as pd
from typing import List, Dict, Optional

def find_zones(candles: List[Dict]) -> Dict[str, List[Dict]]:
    """
    کینڈل ڈیٹا کا تجزیہ کرکے سپلائی اور ڈیمانڈ کے زونز تلاش کرتا ہے۔
    """
    if len(candles) < 50:
        return {"supply": [], "demand": []}

    df = pd.DataFrame(candles)
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])

    supply_zones = []
    demand_zones = []

    # ایک سادہ لیکن موثر منطق: ہم ان علاقوں کو تلاش کریں گے جہاں ایک بڑی کینڈل کے بعد
    # قیمت نے تیزی سے حرکت کی ہو۔
    for i in range(1, len(df) - 1):
        # سپلائی زون کی تلاش (Rally-Base-Drop)
        # ایک مضبوط سبز کینڈل، اس کے بعد ایک چھوٹی کینڈل (بیس)، پھر ایک مضبوط سرخ کینڈل
        is_rally = df['close'][i-1] > df['open'][i-1]
        is_base = abs(df['close'][i] - df['open'][i]) < (df['high'][i] - df['low'][i]) * 0.5
        is_drop = df['close'][i+1] < df['open'][i+1] and (df['open'][i+1] - df['close'][i+1]) > (df['high'][i-1] - df['low'][i-1])

        if is_rally and is_base and is_drop:
            zone = {
                "top": df['high'][i],
                "bottom": df['low'][i],
                "strength": (df['open'][i+1] - df['close'][i+1]) / df['close'][i] # گراوٹ کتنی مضبوط تھی
            }
            supply_zones.append(zone)

        # ڈیمانڈ زون کی تلاش (Drop-Base-Rally)
        # ایک مضبوط سرخ کینڈل، اس کے بعد ایک چھوٹی کینڈل (بیس)، پھر ایک مضبوط سبز کینڈل
        is_drop_prev = df['close'][i-1] < df['open'][i-1]
        # is_base پہلے سے کیلکولیٹڈ ہے
        is_rally_next = df['close'][i+1] > df['open'][i+1] and (df['close'][i+1] - df['open'][i+1]) > (df['open'][i-1] - df['close'][i-1])

        if is_drop_prev and is_base and is_rally_next:
            zone = {
                "top": df['high'][i],
                "bottom": df['low'][i],
                "strength": (df['close'][i+1] - df['open'][i+1]) / df['close'][i] # اضافہ کتنا مضبوط تھا
            }
            demand_zones.append(zone)

    # سب سے مضبوط زونز کو فلٹر کریں
    strong_supply = sorted([z for z in supply_zones if z['strength'] > 0.002], key=lambda x: x['strength'], reverse=True)
    strong_demand = sorted([z for z in demand_zones if z['strength'] > 0.002], key=lambda x: x['strength'], reverse=True)

    return {"supply": strong_supply[:3], "demand": strong_demand[:3]} # سب سے اوپر کے 3 زونز واپس کریں

def analyze_price_in_zones(price: float, zones: Dict[str, List[Dict]]) -> Dict[str, Optional[Dict]]:
    """
    یہ چیک کرتا ہے کہ آیا موجودہ قیمت کسی سپلائی یا ڈیمانڈ زون کے اندر ہے۔
    """
    analysis = {"in_supply": None, "in_demand": None}

    for zone in zones.get("supply", []):
        if zone['bottom'] <= price <= zone['top']:
            analysis["in_supply"] = zone
            break # جیسے ہی پہلا زون ملے، لوپ روک دیں

    for zone in zones.get("demand", []):
        if zone['bottom'] <= price <= zone['top']:
            analysis["in_demand"] = zone
            break

    return analysis
      
