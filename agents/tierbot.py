from agents.strategybot import generate_core_signal, fetch_fake_ohlc from agents.patternai import detect_patterns from agents.riskguardian import check_risk from agents.sentinel import check_news from agents.reasonbot import generate_reason from agents.trainerai import get_confidence from agents.tierbot import determine_tier

def generate_final_signal(symbol: str, candles: list) -> dict: tf = "1m"  # default timeframe for real-time signal

# Derive core signal
core = generate_core_signal(symbol, tf)

# Pattern recognition
pattern = detect_patterns(symbol, tf)

# Risk and news
risk = check_risk(symbol, tf)
news = check_news(symbol)

# Signal reason
reason = generate_reason(core, pattern)

# Confidence
confidence = get_confidence(symbol, tf, core, pattern)

# Tier assignment
tier = determine_tier(confidence)

return {
    "symbol": symbol,
    "signal": core,
    "pattern": pattern,
    "risk": risk,
    "news": news,
    "reason": reason,
    "confidence": confidence,
    "tier": tier
}

