# agents/patternai.py

def detect_pattern(symbol: str, candles: list) -> str:
    try:
        if not candles or len(candles) < 2:
            print("[Warning] Not enough candle data.")
            return "NoCandleData"

        latest = candles[-1]
        previous = candles[-2]

        open_price = float(latest.get("open", 0))
        close_price = float(latest.get("close", 0))
        prev_open = float(previous.get("open", 0))
        prev_close = float(previous.get("close", 0))

        if open_price < close_price and prev_open > prev_close:
            return "BullishEngulfing"
        elif open_price > close_price and prev_open < prev_close:
            return "BearishEngulfing"
        else:
            return "NoPattern"
    except Exception as e:
        print(f"[Error] In detect_pattern(): {e}")
        return "PatternError"
