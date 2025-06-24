# src/agents/core_controller.py

from agents.strategybot import generate_core_signal, fetch_ohlc
from agents.patternai import detect_candle_pattern
from agents.riskguardian import evaluate_risk
from agents.sentinel import validate_signal
from agents.reasonbot import assess_context
from agents.trainerai import update_learning_memory
from agents.loggerai import log_ai_decision
from agents.tierbot import assign_signal_tier
from agents.feedback_memory import calculate_confidence_score


def generate_final_signal(symbol: str, candles: list) -> dict:
    """
    God-level signal generator: combines all agents into one fusion decision.
    """

    # 1. Extract closes from candle data
    closes = [float(candle["close"]) for candle in candles]

    # 2. Get OHLC structure
    ohlc = fetch_ohlc(symbol, "1min", closes)
    if not ohlc:
        return {"error": "Not enough data for OHLC extraction"}

    # 3. Core AI strategy signal
    signal = generate_core_signal(symbol, "1min", closes)

    # 4. Detect pattern
    candle_pattern = detect_candle_pattern([
        {
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"])
        } for c in candles[-2:]
    ])

    # 5. Risk Evaluation
    risk_level, risk_score = evaluate_risk(candles)

    # 6. Validate decision
    is_valid = validate_signal(signal, risk_score, 0.8)

    # 7. Explain reasoning
    reason = assess_context(signal, candle_pattern, risk_level, is_valid)

    # 8. Tier tag
    tier = assign_signal_tier(signal, risk_level, candle_pattern)

    # 9. Confidence score
    confidence = calculate_confidence_score(signal, risk_level, tier)

    # 10. AI Decision Logging
    log_ai_decision(signal, reason, ohlc["close"])

    # 11. Memory Logging
    update_learning_memory(symbol, signal, candle_pattern, risk_level, reason)

    return {
        "symbol": symbol,
        "signal": signal,
        "pattern": candle_pattern,
        "risk": risk_level,
        "reason": reason,
        "tier": tier,
        "confidence": round(confidence * 100, 2)
    }
