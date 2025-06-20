# agents/core_controller.py

from agents.strategybot import generate_core_signal
from agents.patternai import detect_patterns
from agents.riskguardian import check_risk
from agents.sentinel import check_news
from agents.reasonbot import generate_reason
from agents.trainerai import get_confidence
from agents.feedback_memory import get_feedback_stats
from agents.tierbot import determine_tier

def generate_final_signal(symbol: str, candles: list):
    tf = "1min"

    # Run core signal logic
    core = generate_core_signal(symbol, tf)

    # Pattern detection
    pattern = detect_patterns(symbol, tf)

    if not core or not pattern:
        return {
            "status": "no-signal",
            "reason": "Missing core or pattern",
            "symbol": symbol
        }

    # Check market risk and news
    risk = check_risk(symbol, tf)
    news = check_news(symbol)

    # Generate reason
    reason = generate_reason(core, pattern)

    # Get confidence score
    confidence = get_confidence(symbol, tf, core, pattern)

    # Read feedback memory
    feedback_data = get_feedback_stats(symbol)
    feedback_list = []
    if feedback_data["total"] > 0:
        accuracy = feedback_data["accuracy"]
        feedback_list = ["positive" if accuracy > 70 else "negative"] * feedback_data["total"]

    # Determine final tier level
    tier = determine_tier(
        confidence=confidence,
        feedback=feedback_list,
        news_blocked=news,
        risk_blocked=risk
    )

    # Final return payload
    return {
        "symbol": symbol,
        "signal": core["signal"],
        "pattern": pattern,
        "risk": "High" if risk else "Normal",
        "news": "Red event" if news else "Clear",
        "reason": reason,
        "confidence": confidence,
        "tier": tier
    }
