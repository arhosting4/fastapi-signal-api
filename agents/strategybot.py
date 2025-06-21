def generate_core_signal(symbol: str, tf: str, closes: list):
    if len(closes) < 5:
        return None

    # Example placeholder logic
    if closes[-1] > closes[-2] > closes[-3]:
        return "BUY"
    elif closes[-1] < closes[-2] < closes[-3]:
        return "SELL"
    else:
        return "HOLD"

def fetch_ohlc(symbol: str, tf: str):
    return []
