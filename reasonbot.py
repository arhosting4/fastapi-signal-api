# filename: reasonbot.py

from typing import Dict, Any, List

def generate_reason(
    core_signal: str,
    pattern_data: Dict[str, str],
    news_data: Dict[str, Any],
    confidence: float,
    strategy_type: str,
    market_regime: str,
    signal_grade: str
) -> str:
    """
    Generates a clear, professional, and strategy-specific reason in English.
    """
    reason_parts: List[str] = []
    signal_action = "BUY" if core_signal == "buy" else "SELL"

    # Part 1: The Core Strategy and Signal Grade
    # This part is tailored to each specific strategy for a unique output.

    if strategy_type == "Breakout-Hunter":
        reason_parts.append(
            f"**{signal_grade} Signal ({strategy_type}):** "
            f"A high-volume {signal_action} breakout was detected after a period of market consolidation (Bollinger Band Squeeze). "
            f"This indicates a potential start of a new, strong directional move."
        )
    elif strategy_type == "Trend-Following":
        reason_parts.append(
            f"**{signal_grade} Signal ({strategy_type}):** "
            f"The system has identified a {signal_action} opportunity aligned with the dominant market trend, as confirmed by key momentum indicators (EMA & Supertrend)."
        )
    elif strategy_type == "Range-Reversal":
        reason_parts.append(
            f"**{signal_grade} Signal ({strategy_type}):** "
            f"An oversold (for BUY) or overbought (for SELL) condition was detected in a ranging market. "
            f"This {signal_action} signal anticipates a price reversion to its mean."
        )
    else:
        reason_parts.append(
            f"**{signal_grade} Signal:** A {signal_action} opportunity has been identified based on our proprietary analysis."
        )

    # Part 2: Confluence and Confirmation Factors
    # Add details about what strengthens the signal.
    
    pattern_type = pattern_data.get("type", "neutral")
    has_pattern_confirmation = (core_signal == "buy" and pattern_type == "bullish") or \
                               (core_signal == "sell" and pattern_type == "bearish")

    if has_pattern_confirmation:
        reason_parts.append(
            f"The signal is further strengthened by a confirming '{pattern_data.get('pattern')}' candlestick pattern."
        )

    # Part 3: Risk Factors and Warnings
    # Clearly state any potential risks.

    if news_data.get("impact") == "High":
        reason_parts.append(
            "**Warning:** A high-impact news event is scheduled, which could introduce significant volatility and increase risk."
        )
    
    return " ".join(reason_parts)

