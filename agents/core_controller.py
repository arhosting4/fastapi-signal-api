# core_controller.py

from agents.strategybot import generate_core_signal, fetch_ohlc
from agents.patternai import detect_patterns
from agents.riskguardian import check_risk
from agents.sentinel import check_news
from agents.reasonbot import generate_reason
from agents.trainerai import get_confidence
from agents.tierbot import determine_tier

def generate_final_signal(symbol: str, candles: list) -> dict:
    """
    Main controller to generate the final trading signal.
    It calls all sub-agents, merges results, and returns a unified signal.
    """

    try:
        # Step 1: Get OHLC if needed by other agents (for now, we already have it via candles)
        closes = [float(candle["close"]) for candle in reversed(candles)]

        # Step 2: Core Signal
        signal = generate_core_signal(symbol, "1min", closes)

        # Step 3: Pattern Detection
        pattern = detect_patterns(closes)

        # Step 4: Risk Check
        risk = check_risk(closes)

        # Step 5: News Check
        news = check_news(symbol)

        # Step 6: Reason Generator
        reason = generate_reason(signal, pattern, risk, news)

        # Step 7: Confidence Evaluator
        confidence = get_confidence(closes, signal)

        # Step 8: Tier Decision
        tier = determine_tier(confidence)

        return {
            "symbol": symbol,
            "signal": signal,
            "pattern": pattern,
            "risk": risk,
            "news": news,
            "reason": reason,
            "confidence": confidence,
            "tier": tier
        }

    except Exception as e:
        return {
            "error": "Failed to generate signal",
            "details": str(e)
        }
