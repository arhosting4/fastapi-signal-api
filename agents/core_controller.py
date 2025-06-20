# agents/core_controller.py

from agents.strategybot import generate_core_signal
from agents.patternai import detect_patterns
from agents.riskguardian import check_risk
from agents.sentinel import check_news
from agents.reasonbot import generate_reason
from agents.trainerai import get_confidence

def generate_final_signal(symbol: str, candles: list):
    tf = "1min"

    signal = generate_core_signal(symbol, tf, candles)
    pattern = detect_patterns(symbol, tf, candles)
    risk = check_risk(symbol, tf)
    news = check_news(symbol)

    if signal == "no-signal" or pattern == "no-pattern":
        return {
            "status": "no-signal",
            "reason": "Core or pattern failed"
        }

    if risk:
        return {
            "status": "blocked",
            "reason": "High market risk"
        }

    if news:
        return {
            "status": "blocked",
            "reason": "Red news event"
        }

    reason = generate_reason(signal, pattern)
    confidence = get_confidence(symbol, tf, signal, pattern)
    tier = "Tier 1" if confidence > 80 else "Tier 2"

    return {
        "symbol": symbol,
        "signal": signal,
        "pattern": pattern,
        "risk": risk,
        "news": news,
        "reason": reason,
        "confidence": confidence,
        "tier": tier
    }
