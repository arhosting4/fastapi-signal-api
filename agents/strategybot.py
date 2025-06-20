from random import uniform

def fetch_fake_ohlc(pair, tf):
    return {
        "open": uniform(1930, 1950),
        "high": uniform(1951, 1965),
        "low": uniform(1925, 1940),
        "close": uniform(1940, 1955)
    }

def calculate_ema(prices, period):
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = price * k + ema * (1 - k)
    return ema

def calculate_rsi(prices, period=14):
    gains = [max(0, prices[i+1] - prices[i]) for i in range(len(prices)-1)]
    losses = [max(0, prices[i] - prices[i+1]) for i in range(len(prices)-1)]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    rs = avg_gain / (avg_loss + 1e-6)
    return 100 - (100 / (1 + rs))

def generate_core_signal(pair, tf):
    candles = [fetch_fake_ohlc(pair, tf) for _ in range(15)]
    closes = [c["close"] for c in candles]
    ema_fast = calculate_ema(closes[-10:], 10)
    ema_slow = calculate_ema(closes[-14:], 14)
    rsi = calculate_rsi(closes)
    if ema_fast > ema_slow and rsi > 60:
        return {"signal": "BUY", "condition": "EMA uptrend + RSI strong"}
    elif ema_fast < ema_slow and rsi < 40:
        return {"signal": "SELL", "condition": "EMA downtrend + RSI weak"}
    else:
        return None
