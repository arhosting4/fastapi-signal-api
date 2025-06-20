# agents/core_controller.py

from agents.patternai import detect_patterns
from agents.strategybot import generate_core_signal
from agents.sentinel import check_news
from agents.riskguardian import check_risk
from agents.reasonbot import generate_reason
from agents.trainerai import get_confidence

def fuse_signals(candles: list, symbol: str):
    """
    Fuses signals from all agents and returns a final decision.
    """

    # 1. Collect decisions from each AI module
    pattern_signal = detect_patterns(candles)
    strategy_signal = generate_core_signal(candles)
    news_status = check_news(symbol)
    risk_level = check_risk(candles)
    reason = generate_reason(candles)
    confidence = get_confidence(candles)

    # 2. Simple Decision Fusion Logic
    votes = [pattern_signal, strategy_signal]
    buy_votes = votes.count("buy")
    sell_votes = votes.count("sell")

    # 3. Risk and News Filters
    if risk_level == "high" or news_status == "volatile":
        return {
            "signal": "no-trade",
            "reason": f"Filtered due to risk ({risk_level}) or news ({news_status})"
        }

    # 4. Final Decision
    if buy_votes > sell_votes:
        final_signal = "buy"
    elif sell_votes > buy_votes:
        final_signal = "sell"
    else:
        final_signal = "no-signal"

    return {
        "signal": final_signal,
        "confidence": confidence,
        "reason": reason,
        "votes": {
            "pattern": pattern_signal,
            "strategy": strategy_signal
        }
    }
