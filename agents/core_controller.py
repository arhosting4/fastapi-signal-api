# src/agents/core_controller.py

from .strategybot import generate_core_signal, fetch_ohlc
from .patternai import detect_pattern
from .riskguardian import assess_risk
from .sentinel import fetch_news_impact
from .reasonbot import generate_reason
from .trainerai import auto_tune_confidence
from .tierbot import classify_tier
from .loggerai import log_signal

def generate_final_signal(symbol: str, candles: list) -> dict:
    # Step 1: Extract price closes
    closes = [float(c["close"]) for c in candles[::-1]]  # oldest to newest
    ohlc = fetch_ohlc(symbol, "1min", closes)

    if not ohlc:
        return {"error": "Insufficient candle data"}

    # Step 2: Run core signal logic
    signal = generate_core_signal(symbol, "1min", closes)

    # Step 3: Pattern recognition
    pattern = detect_pattern(closes)

    # Step 4: Risk evaluation
    risk = assess_risk(closes)

    # Step 5: News/Sentiment
    news = fetch_news_impact(symbol)

    # Step 6: Reason generation
    reason = generate_reason(signal, pattern, risk, news)

    # Step 7: Confidence scoring
    confidence = 0.8 if signal in ["buy", "sell"] else 0.5
    tuned_confidence = auto_tune_confidence(confidence, symbol, signal)

    # Step 8: Tier classification
    tier = classify_tier(tuned_confidence)

    # Step 9: Log final signal to memory
    log_signal(symbol, signal, tuned_confidence, pattern, risk, reason, tier)

    return {
        "symbol": symbol,
        "signal": signal,
        "pattern": pattern,
        "risk": risk,
        "news": news,
        "reason": reason,
        "confidence": round(tuned_confidence * 100, 2),
        "tier": tier
    }
