# src/agents/core_controller.py

from agents.strategybot import generate_core_signal, fetch_ohlc
from agents.patternai import detect_candle_pattern
from agents.tierbot import assign_tier
from agents.logger import log_signal
from agents.loggerai import analyze_past_signals
from agents.trainerai import train_ai_memory
from agents.sentinel import sentinel_guard
from agents.riskguardian import assess_risk
from agents.reasonbot import generate_reason

def generate_final_signal(symbol: str, candles: list) -> dict:
    """
    Main god-level fusion controller.
    Takes raw OHLC data, routes through all agents, and returns final signal decision.
    """

    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]

    # Sentinel guard check
    sentinel = sentinel_guard(symbol, highs, lows, closes)
    if not sentinel["safe"]:
        return {
            "signal": "wait",
            "pattern": "None",
            "risk": "High Risk",
            "news": "None",
            "reason": sentinel["alert"],
            "confidence": 0,
            "tier": "Blocked",
        }

    # Core signal
    core_signal = generate_core_signal(symbol, "1min", closes)

    # Pattern detection
    pattern = detect_candle_pattern(candles)

    # Risk analysis
    risk = assess_risk(symbol, highs, lows, pattern)

    # Tier assignment
    tier = assign_tier(core_signal, pattern, risk)

    # Reasoning
    reason = generate_reason(core_signal, pattern, risk, tier, news="None")

    # LoggerAI memory reference
    memory = analyze_past_signals(symbol)

    # AI training simulation
    trainer = train_ai_memory(symbol)

    # Final confidence
    confidence = 70  # base
    if tier.startswith("Tier 1"):
        confidence += 15
    elif tier.startswith("Tier 2"):
        confidence += 8
    elif tier.startswith("Tier 3"):
        confidence += 3
    if risk == "Low Risk":
        confidence += 5
    elif risk == "High Risk":
        confidence -= 10

    confidence = min(100, max(0, confidence))

    # Log this decision
    log_signal({
        "symbol": symbol,
        "signal": core_signal,
        "pattern": pattern,
        "tier": tier,
        "risk": risk,
        "confidence": confidence,
        "reason": reason,
    })

    return {
        "signal": core_signal,
        "pattern": pattern,
        "risk": risk,
        "news": "None",
        "reason": reason,
        "confidence": confidence,
        "tier": tier,
        "memory_insight": memory,
        "ai_training": trainer
    }
