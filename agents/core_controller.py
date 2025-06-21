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

        # ✅ Convert candle data to closing prices list
        closes = [float(candle["close"]) for candle in candles[::-1]]

        # ✅ Step 1: Core AI strategy signal
        strategy_signal = generate_core_signal(symbol, tf, closes)
        if not strategy_signal or strategy_signal == "wait":
            return {"status": "no-signal", "error": "Strategy failed or no trend"}

        # ✅ Step 2: Detect chart pattern
        pattern_data = detect_patterns(symbol, tf)
        pattern = pattern_data.get("pattern", "Unknown")

        if not pattern:
            return {"status": "no-signal", "error": "No pattern detected"}

        # ✅ Step 3: Risk check
        if check_risk(symbol, closes):
            return {"status": "blocked", "error": "High market risk"}

        # ✅ Step 4: News filter
        # (Empty list used for now — can integrate live news later)
        if check_news(symbol, []):
            return {"status": "blocked", "error": "Red news event"}

        # ✅ Step 5: Reasoning
        reason = generate_reason(strategy_signal, pattern)

        # ✅ Step 6: Confidence
        confidence = get_confidence(symbol, tf, strategy_signal, pattern)

        # ✅ Step 7: Tier level
        tier = get_tier(confidence)

        # ✅ Step 8: Final signal result
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
