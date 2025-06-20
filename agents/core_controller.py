# agents/core_controller.py

from agents.strategybot import generate_core_signal
from agents.patternai import detect_patterns
from agents.riskguardian import check_risk
from agents.sentinel import check_news
from agents.reasonbot import generate_reason
from agents.trainerai import get_confidence

def generate_final_signal(symbol: str):
    signal = generate_core_signal(symbol)
    pattern = detect_patterns(symbol)
    risk = check_risk(symbol)
    news = check_news(symbol)
    reason = generate_reason(signal, pattern)
    confidence = get_confidence(signal, pattern, risk, news)

    if signal == "no-signal" or pattern == "no-pattern":
        return {
            "status": "no-signal",
            "reason": "Core or pattern failed"
        }

    return {
        "symbol": symbol,
        "signal": signal,
        "pattern": pattern,
        "risk": risk,
        "news": news,
        "reason": reason,
        "confidence": confidence
    }
