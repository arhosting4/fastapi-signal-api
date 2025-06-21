# src/agents/reasonbot.py

def generate_reason(core_signal: str, pattern_signal: str) -> str:
    """
    Generates a natural language reason for the signal decision
    based on core and pattern alignment.
    """
    if core_signal == "buy" and pattern_signal == "buy":
        return "Strong bullish confirmation from both strategy and pattern"
    elif core_signal == "sell" and pattern_signal == "sell":
        return "Strong bearish confirmation from both strategy and pattern"
    elif core_signal == "buy" and pattern_signal == "sell":
        return "Strategy suggests buying, but pattern warns of reversal"
    elif core_signal == "sell" and pattern_signal == "buy":
        return "Strategy suggests selling, but pattern warns of pullback"
    else:
        return "Mixed or neutral signals; no strong alignment"
