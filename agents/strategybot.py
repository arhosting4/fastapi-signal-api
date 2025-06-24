# src/agents/strategybot.py

def generate_core_signal(symbol: str, tf: str, closes: list) -> str:
    """
    Generates basic buy/sell/wait signal based on last 3 close values.
    """
    if len(closes) < 3:
        return "wait"

    if closes[-1] > closes[-2] > closes[-3]:
        return "buy"
    elif closes[-1] < closes[-2] < closes[-3]:
        return "sell"
    else:
        return "wait"

def fetch_ohlc(symbol: str, interval: str, data: list) -> dict:
    """
    Simulates fetching OHLCV data from close list.
    """
    if len(data) < 5:
        return {}

    return {
        "open": data[-5],
        "high": max(data[-5:]),
        "low": min(data[-5:]),
        "close": data[-1],
        "volume": 1000  # Placeholder for volume
    }
