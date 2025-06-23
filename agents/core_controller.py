# src/agents/core_controller.py

from agents.strategybot import generate_core_signal, fetch_ohlc
from agents.patternai import detect_pattern
from agents.riskguardian import evaluate_risk
from agents.reasonbot import generate_reason
from agents.tierbot import assign_tier
from agents.trainerai import calculate_confidence
from agents.feedback_memory import save_signal_to_memory
from agents.logger import log_signal
from agents.sentinel import check_news_event


def generate_final_signal(symbol: str, candles: list) -> dict:
    """
    Central AI Signal Controller – combines all logic layers
    """
    try:
        closes = [float(c['close']) for c in candles[::-1]]  # Most recent last
        tf = "1m"

        # Step 1: Extract OHLC
        ohlc = fetch_ohlc(symbol, tf, closes)

        # Step 2: Base Signal
        signal = generate_core_signal(symbol, tf, closes)

        # Step 3: Pattern Detection
        pattern = detect_pattern(candles)

        # Step 4: Risk Evaluation
        risk = evaluate_risk(candles)

        # Step 5: News Event Filter
        news_flag = check_news_event(symbol)

        # Step 6: Signal Reason
        reason = generate_reason(signal, pattern, risk)

        # Step 7: Confidence Score
        confidence = calculate_confidence(signal, pattern, risk)

        # Step 8: Tier Label
        tier = assign_tier(confidence)

        # Final Logic Adjustments
        if risk == "high" or news_flag:
            signal = "wait"
            reason = "High risk or sensitive event – pausing"

        # Build result
        result = {
            "symbol": symbol,
            "signal": signal,
            "pattern": pattern,
            "risk": risk,
            "news": "⚠️ Event" if news_flag else "Clear",
            "reason": reason,
            "confidence": confidence,
            "tier": tier
        }

        # Step 9: Save to memory & log
        save_signal_to_memory(result)
        log_signal(result)

        return result

    except Exception as e:
        return {"error": "⚠️ Signal generation failed", "details": str(e)}
