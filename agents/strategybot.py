# strategybot.py

def generate_core_signal(symbol: str, tf: str, closes: list):
    """
    Basic strategy to determine signal from closing price trends.
    """
    if len(closes) < 5:
        return None

    recent_closes = closes[-5:]
    avg = sum(recent_closes) / len(recent_closes)

    if recent_closes[-1] > avg:
        return "BUY"
    elif recent_closes[-1] < avg:
        return "SELL"
    else:
        return "HOLD"

def fetch_ohlc(symbol: str, interval: str = "1min", limit: int = 50):
    """
    Simulate fetching OHLC data — Replace with actual API in production.
    """
    import random
    return [{"open": random.uniform(1800, 1900),
             "high": random.uniform(1900, 1920),
             "low": random.uniform(1780, 1850),
             "close": random.uniform(1800, 1900)} for _ in range(limit)]
