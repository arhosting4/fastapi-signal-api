def check_risk(symbol: str, closes: list) -> bool:
    if len(closes) < 2:
        return False

    last_close = float(closes[-1]['close'])
    prev_close = float(closes[-2]['close'])

    # Basic example risk rule: avoid trades if close difference > 2%
    change_percent = abs(last_close - prev_close) / prev_close * 100

    if change_percent > 2.0:
        return False

    return True
