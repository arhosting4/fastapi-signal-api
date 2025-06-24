# agents/core_controller.py

from agents.strategybot import generate_core_signal, fetch_ohlc
from agents.riskguardian import evaluate_risk
from agents.sentinel import detect_pattern
from agents.reasonbot import generate_reason
from agents.trainerai import estimate_confidence
from agents.patternai import analyze_market_pattern
from agents.tierbot import determine_tier
from agents.loggerai import log_signal

def generate_final_signal(symbol: str, candles: list) -> dict:
    """
    God-level fusion of all AI layers to generate the final trading signal.
    """
    # Extract closing prices
    closes = [float(candle["close"]) for candle in candles]

    # Core signal logic (momentum)
    signal = generate_core_signal(symbol, "1min", closes)

    # Risk layer
    risk = evaluate_risk(closes)

    # OHLC structure for downstream agents
    ohlc = fetch_ohlc(symbol, "1min", closes)

    # Pattern detection
    pattern = detect_pattern(ohlc)

    # Reason generator
    reason = generate_reason(signal, pattern, risk)

    # Market-based pattern (macro layer)
    macro_pattern = analyze_market_pattern(closes)

    # Confidence estimator
    confidence = estimate_confidence(signal, closes)

    # Tier classification
    tier = determine_tier(confidence, risk)

    # Logging (optional but useful for debugging or monitoring)
    log_signal(symbol, signal, confidence, pattern, reason, tier)

    return {
        "signal": signal,
        "risk": risk,
        "pattern": pattern,
        "reason": reason,
        "macro_pattern": macro_pattern,
        "confidence": confidence,
        "tier": tier
    }
