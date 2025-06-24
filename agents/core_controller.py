# src/agents/core_controller.py

from agents.patternai import detect_pattern
from agents.riskguardian import evaluate_risk
from agents.sentinel import validate_signal
from agents.reasonbot import generate_reasoning
from agents.tierbot import assign_signal_tier
from agents.trainerai import log_signal_feedback
from agents.loggerai import send_telegram_message
from agents.strategybot import generate_core_signal, fetch_ohlc

def generate_final_signal(symbol: str, candles: list) -> dict:
    """
    Master controller: uses all AI agents to process candles and return final god-level signal.
    """
    closes = [float(c["close"]) for c in candles]
    tf = "1min"

    # Step 1: Generate signal from core logic
    signal = generate_core_signal(symbol, tf, closes)

    # agents/core_controller.py (inside generate_final_signal function)

from agents.patternai import detect_pattern

try:
    pattern = detect_pattern(symbol, candles)
    if not pattern:
        pattern = "NoPattern"
except Exception as e:
    print(f"[Error] detect_pattern failed: {e}")
    pattern = "PatternError"

    # Step 3: Risk analysis
    risk = evaluate_risk(volatility=2.5, spread=1.8, news_impact=4.0)

    # Step 4: Assign tier
    tier = assign_signal_tier(pattern, risk, signal)

    # Step 5: Reason generation
    reason = generate_reasoning(signal, pattern, risk)

    # Step 6: Final validation
    is_valid = validate_signal(signal, risk, tier)

    if not is_valid:
        return {
            "symbol": symbol,
            "signal": "wait",
            "pattern": pattern,
            "risk": risk,
            "news": "neutral",
            "reason": "Signal conditions not met.",
            "confidence": 0,
            "tier": "C"
        }

    # Step 7: Compose message
    confidence = {"A": 95, "B": 80, "C": 65}[tier]
    message = (
        f"📡 *{signal.upper()}* Signal for *{symbol}*\n\n"
        f"🧠 *Pattern:* {pattern}\n"
        f"📊 *Risk:* {risk}\n"
        f"📰 *News:* neutral\n"
        f"🔍 *Reason:* {reason}\n"
        f"🎯 *Confidence:* {confidence}%\n"
        f"🏅 *Tier:* {tier}"
    )

    # Step 8: Send message & log
    send_telegram_message(message)
    log_signal_feedback(symbol, signal, success=True)

    # Step 9: Return final result
    return {
        "symbol": symbol,
        "signal": signal,
        "pattern": pattern,
        "risk": risk,
        "news": "neutral",
        "reason": reason,
        "confidence": confidence,
        "tier": tier
    }
