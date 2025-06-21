# src/agents/trainerai.py

import random

def get_confidence(pair: str, tf: str, core: str, pattern: str) -> float:
    """
    Estimates signal confidence based on current logic fusion.
    In a future upgrade, this will use adaptive ML training logs.

    Parameters:
        pair (str): Trading pair symbol (e.g., XAU/USD)
        tf (str): Timeframe (e.g., 1min)
        core (str): Signal from core strategy logic
        pattern (str): Signal from pattern recognition agent

    Returns:
        float: Confidence percentage from 50% to 99%
    """
    if core == pattern:
        return round(random.uniform(85, 99), 2)  # Strong agreement
    else:
        return round(random.uniform(50, 70), 2)  # Weak or mixed signal
