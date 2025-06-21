from agents.strategybot import generate_core_signal, fetch_ohlc from agents.patternai import detect_patterns from agents.riskguardian import check_risk from agents.sentinel import check_news from agents.reasonbot import generate_reason from agents.trainerai import get_confidence from agents.tierbot import determine_tier

def generate_final_signal(symbol: str, candles: list): # Extract necessary values closes = [float(candle['close']) for candle in candles] tf = "1min"

# Generate signal using AI agents
core_signal = generate_core_signal(symbol, tf, closes)
pattern = detect_patterns(symbol, tf, closes)

if not core_signal or not pattern:
    return {"signal": "no-signal", "reason": "Missing core or pattern analysis"}

risk = check_risk(symbol, tf, closes)
if risk:
    return {"signal": "blocked", "risk": "high", "reason": "Risk filter active"}

news_blocked = check_news(symbol)
if news_blocked:
    return {"signal": "blocked", "news": "red", "reason": "Red news detected"}

reason = generate_reason(core_signal, pattern)
confidence = get_confidence(symbol, tf, core_signal, pattern)
tier = determine_tier(confidence)

return {
    "signal": core_signal,
    "pattern": pattern,
    "risk": "low",
    "news": "clear",
    "reason": reason,
    "confidence": confidence,
    "tier": tier
}

