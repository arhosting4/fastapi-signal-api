# src/agents/core_controller.py

from agents.strategybot import generate_core_signal, fetch_ohlc
from agents.riskguardian import assess_risk
from agents.sentinel import news_sentiment
from agents.reasonbot import generate_reason
from agents.loggerai import record_log
from agents.trainerai import log_signal_feedback
from agents.patternai import detect_pattern
from agents.tierbot import get_tier

def generate_final_signal(symbol: str, candles: list) -> dict:
    try:
        # Validate candle input
        if not candles or len(candles) < 5:
            raise ValueError("Insufficient candle data")

        closes = [float(c["close"]) for c in candles if "close" in c]

        # Core strategy decision
        tf = "1min"
        signal = generate_core_signal(symbol, tf, closes)
        ohlc = fetch_ohlc(symbol, tf, closes)

        # AI layers
        pattern = detect_pattern(symbol, candles)
        risk = assess_risk(ohlc)
        news = news_sentiment(symbol)
        reason = generate_reason(symbol, signal, pattern, risk, news)
        confidence = 95 if signal != "wait" else 50
        tier = get_tier(signal, confidence)

        # Log and training memory
        record_log(symbol, signal, risk, news, reason, tier)
        log_signal_feedback(symbol, signal, success=(signal != "wait"))

        # Final structured response
        return {
            "symbol": symbol,
            "final_signal": signal,
            "risk": risk,
            "tier": tier,
            "pattern": pattern,
            "news": news,
            "reason": reason,
            "confidence": confidence,
            "validated": True
        }

    except Exception as e:
        print(f"[CoreController Error] {e}")
        return {
            "symbol": symbol,
            "error": "❌ Signal generation failed",
            "details": str(e),
            "validated": False
        }
