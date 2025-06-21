import random

def fetch_ohlc(symbol: str, tf: str): # Simulate 10 random candles (for mock/testing) return [ { "open": round(random.uniform(100, 2000), 2), "high": round(random.uniform(100, 2000), 2), "low": round(random.uniform(100, 2000), 2), "close": round(random.uniform(100, 2000), 2) } for _ in range(10) ]

def generate_core_signal(symbol: str, tf: str, closes: list): if len(closes) < 5: return None

# Simple trend-based strategy (placeholder for advanced AI)
avg_recent = sum(closes[-3:]) / 3
avg_past = sum(closes[:3]) / 3

if avg_recent > avg_past * 1.01:
    return "buy"
elif avg_recent < avg_past * 0.99:
    return "sell"
else:
    return "wait"
