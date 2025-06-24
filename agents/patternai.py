# agents/patternai.py

def detect_pattern(candles: list) -> dict:
    if not candles or len(candles) < 3:
        return {"pattern": None, "strength": 0}

    last = candles[-1]
    prev = candles[-2]
    before_prev = candles[-3]

    # Example basic pattern logic (you can expand later)
    if last["close"] > last["open"] and prev["close"] < prev["open"]:
        return {"pattern": "bullish_engulfing", "strength": 70}
    elif last["close"] < last["open"] and prev["close"] > prev["open"]:
        return {"pattern": "bearish_engulfing", "strength": 70}
    else:
        return {"pattern": "no_clear_pattern", "strength": 20}
