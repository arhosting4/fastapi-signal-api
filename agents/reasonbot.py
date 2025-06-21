def generate_reason(core: str, pattern: str) -> str:
    if core == "buy" and pattern == "bullish engulfing":
        return "Strong bullish signal with bullish engulfing pattern"
    elif core == "sell" and pattern == "bearish engulfing":
        return "Strong bearish signal with bearish engulfing pattern"
    elif core == pattern:
        return "Pattern confirms core trend"
    elif core == "wait" or pattern == "wait" or pattern == "no pattern":
        return "Lack of strong confirmation"
    else:
        return "Mixed signals – exercise caution"
