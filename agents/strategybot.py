# agents/strategybot.py

from typing import List

def fetch_fake_ohlc(symbol: str, tf: str):
    """
    Dummy OHLC generator for testing purposes.
    Replace with real OHLC data fetching logic in production.
    """
    return [
        {"open": 1900.0, "high": 1910.0, "low": 1895.0, "close": 1905.0},
        {"open": 1905.0, "high": 1915.0, "low": 1900.0, "close": 1910.0},
        {"open": 1910.0, "high": 1920.0, "low": 1905.0, "close": 1915.0},
        {"open": 1915.0, "high": 1925.0, "low": 1910.0, "close": 1920.0},
        {"open": 1920.0, "high": 1930.0, "low": 1915.0, "close": 1925.0},
    ]

def generate_core_signal(symbol: str, tf: str, closes: List[float]) -> str:
    """
    Generates a core buy/sell/wait signal based on basic close price pattern.
    More advanced logic can be inserted later.
    """
    if len(closes) < 5:
        return "wait"

    recent_closes = closes[-5:]
    if recent_closes[-1] > recent_closes[0] and all(x < y for x, y in zip(recent_closes, recent_closes[1:])):
        return "buy"
    elif recent_closes[-1] < recent_closes[0] and all(x > y for x, y in zip(recent_closes, recent_closes[1:])):
        return "sell"
    else:
        return "wait"
