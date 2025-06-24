# src/agents/core_controller.py

from agents.strategybot import generate_core_signal
from agents.patternai import detect_candle_pattern
from agents.riskguardian import evaluate_risk
from agents.tierbot import assign_tier
from agents.sentinel import validate_signal
from agents.trainerai import update_learning_memory
from agents.loggerai import log_ai_decision
from agents.reasonbot import assess_context
from agents.feedback_memory import record_feedback

def generate_final_signal(symbol: str, tf: str, closes: list) -> dict:
    if len(closes) < 5:
        return {"status": "wait", "reason": "insufficient data"}

    # 1. Core strategy signal
    base_signal = generate_core_signal(symbol, tf, closes)

    # 2. Pattern recognition layer
    pattern = detect_candle_pattern(closes)

    # 3. Risk management layer
    risk_score = evaluate_risk(closes)

    # 4. Tier assignment logic
    tier = assign_tier(closes)

    # 5. Confidence weighting (example: dummy logic)
    confidence = 0.7 if pattern == base_signal and base_signal != "wait" else 0.4

    # 6. AI Reasoning Engine
    context_reasoning = assess_context(symbol, closes, base_signal, pattern, risk_score, tier)

    # 7. AI Signal Validation
    if not validate_signal(base_signal, risk_score, pattern):
        base_signal = "wait"
        confidence = 0.0

    # 8. Trainer AI — update feedback memory
    update_learning_memory(symbol, base_signal, closes)

    # 9. Record for long-term feedback
    record_feedback(symbol, tf, base_signal, risk_score)

    # 10. Log final decision
    log_ai_decision(symbol, base_signal, confidence, context_reasoning)

    # Final signal package
    return {
        "status": "ok",
        "signal": base_signal,
        "confidence": round(confidence, 2),
        "risk": round(risk_score, 2),
        "tier": tier,
        "reason": context_reasoning
    }
