from agents.strategybot import generate_core_signal, fetch_ohlc
from agents.patternai import detect_patterns
from agents.riskguardian import check_risk
from agents.sentinel import check_news
from agents.reasonbot import generate_reason
from agents.trainerai import get_confidence
from agents.tierbot import determine_tier


def generate_final_signal(symbol: str, candles: list) -> dict:
    """
    Generates the final AI signal for a given symbol using multi-layer strategy fusion.
    """

    # Step 1: Get core signal and OHLC structure
    core_signal, ohlc = generate_core_signal(candles), fetch_ohlc(candles)

    # Step 2: Detect patterns (if needed)
    pattern = detect_patterns(ohlc)

    # Step 3: Evaluate risk profile based on market structure
    risk = check_risk(ohlc)

    # Step 4: Check real-time news or sentiment-based influence
    news = check_news(symbol)

    # Step 5: Use AI to generate explanation for decision
    reason = generate_reason(core_signal, pattern, risk, news)

    # Step 6: Measure signal confidence using training memory
    confidence = get_confidence(symbol, core_signal, candles)

    # Step 7: Determine tier (priority level) of the signal
    tier = determine_tier(core_signal, risk, confidence)

    # Step 8: Compose final result
    final_result = {
        "symbol": symbol,
        "signal": core_signal,
        "pattern": pattern,
        "risk": risk,
        "news": news,
        "reason": reason,
        "confidence": confidence,
        "tier": tier
    }

    return final_result
