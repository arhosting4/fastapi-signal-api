def generate_core_signal(symbol: str, tf: str, closes: list) -> str:
    if len(closes) < 5:
        return "wait"
    if closes[-1] > closes[-2] > closes[-3]:
        return "buy"
    elif closes[-1] < closes[-2] < closes[-3]:
        return "sell"
    else:
        return "wait"

def fetch_ohlc(symbol: str, interval: str, data: list) -> dict:
    if len(data) < 5:
        return {}
    return {
        "open": data[-5],
        "high": max(data[-5:]),
        "low": min(data[-5:]),
        "close": data[-1],
        "volume": 1000
    }
