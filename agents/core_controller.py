# agents/core_controller.py

from agents.strategybot import generate_core_signal, fetch_ohlc
from agents.patternai import detect_candle_pattern
from agents.riskguardian import evaluate_risk
from agents.tierbot import assign_tier
from agents.sentinel import validate_signal
from agents.trainerai import learn_from_history
from agents.reasonbot import generate_reason

def generate_final_signal(symbol: str, tf: str, closes: list):
    if len(closes) < 5:
        return {"status": "error", "message": "Not enough data"}

    # Step 1: Raw Signal Logic
    raw_signal = generate_core_signal(symbol, tf, closes)

    # Step 2: OHLC data (mocked)
    ohlc = fetch_ohlc(symbol, tf, closes)

    # Step 3: Candle Pattern Detection
    pattern = detect_candle_pattern(closes)
    if pattern in ["bearish", "bullish"] and pattern != raw_signal:
        pattern_opinion = "conflict"
    else:
        pattern_opinion = "aligned"

    # Step 4: Risk Filter
    risk_decision = evaluate_risk(symbol, tf)

    # Step 5: Assign Tier
    tier = assign_tier(symbol)

    # Step 6: Memory Learning Influence
    memory_bias = learn_from_history(symbol, raw_signal, ohlc["close"], tf)

    # Step 7: Validate Signal
    if risk_decision == "reject" or memory_bias == "reject":
        final_signal = "wait"
    else:
        final_signal = raw_signal

    # Step 8: Generate Reasoning
    reason = generate_reason(
        symbol=symbol,
        tf=tf,
        signal=final_signal,
        tier=tier,
        pattern=pattern,
        pattern_opinion=pattern_opinion,
        risk=risk_decision,
        memory=memory_bias
    )

    return {
        "status": "ok",
        "symbol": symbol,
        "tf": tf,
        "signal": final_signal,
        "price": ohlc["close"],
        "reason": reason
    }
