def generate_core_signal(symbol: str, tf: str, closes: list):
    if len(closes) < 5:
        return None

    # Sample core logic for strategy signal
    last = closes[-1]
    prev = closes[-2]

    if float(last['close']) > float(prev['close']):
        return "BUY"
    elif float(last['close']) < float(prev['close']):
        return "SELL"
    else:
        return "HOLD"


def fetch_ohlc(closes: list):
    # Converts raw data to OHLC list for further agents
    ohlc = []
    for candle in closes:
        ohlc.append({
            'open': float(candle['open']),
            'high': float(candle['high']),
            'low': float(candle['low']),
            'close': float(candle['close']),
            'datetime': candle['datetime']
        })
    return ohlc
