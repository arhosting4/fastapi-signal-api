from agents.strategybot import generate_core_signal, fetch_ohlc
from agents.patternai import detect_patterns
from agents.riskguardian import check_risk
from agents.sentinel import check_news
from agents.reasonbot import generate_reason
from agents.trainerai import get_confidence
from agents.tierbot import determine_tier

def generate_final_signal(symbol: str, tf: str) -> dict:
    # Step 1: Get market data
    closes = fetch_ohlc(symbol, tf)
    if not closes or len(closes) < 5:
        return {"status": "error", "message": "Not enough data"}

    # Step 2: Core strategy signal
    core_signal = generate_core_signal(symbol, tf, closes)

    # Step 3: Pattern detection
    pattern = detect_patterns(closes)

    # Step 4: Risk filter
    is_safe = check_risk(symbol, closes)

    # Step 5: News sentiment
    news_ok = check_news(symbol)

    # Step 6: Reason analysis
    reason = generate_reason(core_signal, pattern)

    # Step 7: Confidence
    confidence = get_confidence(symbol, tf)

    # Step 8: Tier classification
    tier = determine_tier(confidence, pattern, is_safe)

    # Step 9: Compile final response
    return {
        "symbol": symbol,
        "timeframe": tf,
        "signal": core_signal,
        "pattern": pattern,
        "risk_clear": is_safe,
        "news_sentiment": news_ok,
        "reason": reason,
        "confidence": confidence,
        "tier": tier,
        "status": "ok"
    }
