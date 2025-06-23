# src/agents/core_controller.py

from agents.strategybot import generate_core_signal
from agents.patternai import detect_candle_pattern
from agents.reasonbot import assess_context
from agents.riskguardian import evaluate_risk
from agents.tierbot import assign_tier
from agents.loggerai import log_ai_decision
from agents.trainerai import learn_from_outcome
from agents.sentinel import validate_signal

def generate_final_signal(symbol: str, tf: str, data: list) -> dict:
    """
    Combines all AI modules to generate a final validated signal.
    """

    closes = data
    if len(closes) < 5:
        return {"status": "error", "message": "Insufficient data"}

    signal = generate_core_signal(symbol, tf, closes)
    pattern = detect_candle_pattern(closes)
    context = assess_context(symbol)
    risk = evaluate_risk(symbol, closes)
    tier = assign_tier(symbol, tf, closes)

    final_signal = signal
    if signal != pattern:
        final_signal = "wait"  # conflict found

    is_valid = validate_signal(final_signal, context["trend"], tier)
    if not is_valid:
        final_signal = "wait"

    log_ai_decision(symbol, tf, signal, pattern, context, risk, tier, final_signal)
    learn_from_outcome(symbol, tf, final_signal)

    return {
        "status": "ok",
        "symbol": symbol,
        "signal": final_signal,
        "price": closes[-1]
    }
