# src/agents/strategybot.py

def generate_core_signal(symbol: str, tf: str, closes: list) -> str:
    """
    Generates a core trading signal (buy, sell, or wait) based on simple price action.
    This is a basic strategy and can be replaced with more complex algorithms.

    Parameters:
        symbol (str): Trading pair symbol (e.g., XAU/USD).
        tf (str): Timeframe (e.g., 1min).
        closes (list): List of closing prices, from oldest to newest.

    Returns:
        str: "buy", "sell", or "wait".
    """
    if len(closes) < 5: # Need at least 5 candles for this simple strategy
        return "wait"

    # Simple trend detection based on last 3 candles
    # Check if the last three closing prices are consistently increasing (uptrend)
    if closes[-1] > closes[-2] and closes[-2] > closes[-3]:
        return "buy"
    # Check if the last three closing prices are consistently decreasing (downtrend)
    elif closes[-1] < closes[-2] and closes[-2] < closes[-3]:
        return "sell"
    else:
        return "wait"

# Note: fetch_ohlc is now handled in main.py's fetch_real_ohlc_data
# and generate_final_signal in fusion_engine.py will pass the 'candles' list.
# So, this file only needs the core signal generation logic.
