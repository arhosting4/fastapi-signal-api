def check_risk(symbol: str, closes: list) -> bool: if len(closes) < 2: return False

# High volatility risk check (placeholder logic)
volatility = abs(closes[-1] - closes[-2]) / closes[-2]
return volatility > 0.03  # >3% change in last candle

