# src/agents/sentinel.py

def check_news(symbol: str, high_impact_events: list) -> bool:
    """
    Returns True if there is a high-impact news event related to the symbol.
    Used to avoid trading during risky periods.
    """
    if not symbol or not high_impact_events:
        return False

    symbol_lower = symbol.lower()
    for event in high_impact_events:
        if symbol_lower in event.lower():
            return True

    return False
