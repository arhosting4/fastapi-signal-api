# src/agents/riskguardian.py

def check_risk(symbol: str, closes: list) -> bool:
    """
    Basic volatility/risk check:
    If price changed too sharply in last 2 candles, flag as risky.
    """
    if len(closes) < 3:
        return False

    last_change = abs(closes[-1] - closes[-2])
    prev_change = abs(closes[-2] - closes[-3])

    volatility = last_change + prev_change
    average_price = sum(closes[-3:]) / 3

    risk_threshold = 0.03 * average_price  # 3% move considered high-risk

    return volatility > risk_threshold
