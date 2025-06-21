def check_news(symbol: str) -> bool:
    high_impact_events = ["fed", "nfp", "interest rate", "inflation"]

    for event in high_impact_events:
        if event in symbol.lower():
            return True
    return False
