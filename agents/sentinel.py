# agents/sentinel.py

import datetime
import random

def analyze_market_context(symbol: str) -> str:
    """
    Simulates a macro-level context filter (like news impact or session strength).
    Can return: "bullish", "bearish", or "neutral"
    """

    # Use time-based dummy logic for different market sessions
    now = datetime.datetime.utcnow()
    hour = now.hour

    if 0 <= hour < 6:
        session = "Asia"
    elif 6 <= hour < 13:
        session = "Europe"
    elif 13 <= hour < 20:
        session = "US"
    else:
        session = "Late-US"

    # Simulated market mood per session
    session_bias = {
        "Asia": "neutral",
        "Europe": "bullish",
        "US": "bearish",
        "Late-US": "neutral"
    }.get(session, "neutral")

    # Add simulated news noise
    news_randomizer = random.random()
    if news_randomizer > 0.85:
        return "bullish"
    elif news_randomizer < 0.15:
        return "bearish"
    else:
        return session_bias
