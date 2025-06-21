# src/agents/core_controller.py

from agents.strategybot import generate_core_signal
from agents.patternai import detect_patterns
from agents.riskguardian import check_risk
from agents.sentinel import check_news
from agents.reasonbot import generate_reason
from agents.trainerai import get_confidence
from agents.tierbot import get_tier


def generate_final_signal(symbol: str, candles: list):
    """
    Core AI fusion engine combining all agents to generate a god-level trading signal.

    Parameters:
        symbol (str): The trading pair (e.g., XAU/USD).
        candles (list): List of OHLC candles from the API.

    Returns:
        dict: Final AI signal output with full intelligence context.
    """
    try:
        tf = "1min"

        # Step 1: Get core AI strategy signal
        strategy_signal = generate_core_signal(symbol, tf)
        if not strategy_signal:
            return {"status": "no-signal", "error": "Strategy failed"}

        # Step 2: Detect chart patterns
        pattern = detect_patterns(symbol, tf)
        if not pattern:
            return {"status": "no-signal", "error": "Pattern not found"}

        # Step 3: Check for high-risk conditions
        if check_risk(symbol, tf):
            return {"status": "blocked", "error": "High market risk"}

        # Step 4: Check news sentinel for red events
        if check_news(symbol):
            return {"status": "blocked", "error": "Red news event detected"}

        # Step 5: Reasoning based on combined signal and pattern
        reason = generate_reason(strategy_signal, pattern)

        # Step 6: AI learns confidence level for the signal
        confidence = get_confidence(symbol, tf, strategy_signal, pattern)

        # Step 7: Assign AI tier based on confidence
        tier = get_tier(confidence)

        # Step 8: Return the fused god-level signal
        return {
            "symbol": symbol,
            "signal": strategy_signal,
            "pattern": pattern,
            "risk": "Normal",
            "news": "Clear",
            "reason": reason,
            "confidence": round(confidence, 2),
            "tier": tier
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
