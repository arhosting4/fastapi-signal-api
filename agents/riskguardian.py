def check_risk(symbol: str, closes: list) -> bool:
    if len(closes) < 2:
        return False

    risk_ratio = abs(closes[-1] - closes[-2]) / closes[-2]
    return risk_ratio < 0.03
