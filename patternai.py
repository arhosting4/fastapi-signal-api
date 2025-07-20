import pandas as pd
import pandas_ta as ta

def detect_patterns(candles: list) -> dict:
    if not candles or len(candles) < 20:
        return {"pattern": "Insufficient Data", "type": "neutral"}

    df = pd.DataFrame(candles)
    df["open"] = pd.to_numeric(df["open"])
    df["high"] = pd.to_numeric(df["high"])
    df["low"] = pd.to_numeric(df["low"])
    df["close"] = pd.to_numeric(df["close"])

    def get_pattern_value(pattern_series):
        if isinstance(pattern_series, pd.Series) and not pattern_series.empty:
            value = pattern_series.iloc[-1]
            return float(value) if pd.notna(value) else 0.0
        return 0.0

    patterns = {
        "Bullish Engulfing": get_pattern_value(ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"], name="engulfing")),
        "Hammer": get_pattern_value(ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"], name="hammer")),
        "Morning Star": get_pattern_value(ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"], name="morningstar")),
        "Dark Cloud Cover": get_pattern_value(ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"], name="darkcloudcover")),
        "Shooting Star": get_pattern_value(ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"], name="shootingstar")),
        "Evening Star": get_pattern_value(ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"], name="eveningstar")),
    }

    for name, value in patterns.items():
        if value > 0: return {"pattern": name, "type": "bullish"}
        if value < 0: return {"pattern": name, "type": "bearish"}

    return {"pattern": "No Specific Pattern", "type": "neutral"}
    
