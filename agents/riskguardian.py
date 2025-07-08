# src/agents/riskguardian.py

def check_risk(symbol: str, closes: list) -> bool:
    """
    Performs a basic volatility/risk check.
    Flags as risky if the price has changed too sharply in the last few candles.

    Parameters:
        symbol (str): Trading pair symbol (e.g., XAU/USD).
        closes (list): List of closing prices, from oldest to newest.

    Returns:
        bool: True if market is considered risky, False otherwise.
    """
    if len(closes) < 5: # Need at least 5 candles to assess recent volatility
        return False

    # Calculate percentage change for the last few candles
    # We'll look at the last 3 candles for significant movement
    last_candle_change_pct = abs((closes[-1] - closes[-2]) / closes[-2]) if closes[-2] != 0 else 0
    second_last_candle_change_pct = abs((closes[-2] - closes[-3]) / closes[-3]) if closes[-3] != 0 else 0
    third_last_candle_change_pct = abs((closes[-3] - closes[-4]) / closes[-4]) if closes[-4] != 0 else 0

    # Define a threshold for high volatility (e.g., 1% change in a single candle)
    # This threshold can be adjusted based on the asset and timeframe
    VOLATILITY_THRESHOLD_PCT = 0.015 # 1.5% change in a single candle

    # If any of the last 3 candles show a very high percentage change, flag as risky
    if (last_candle_change_pct > VOLATILITY_THRESHOLD_PCT or
        second_last_candle_change_pct > VOLATILITY_THRESHOLD_PCT or
        third_last_candle_change_pct > VOLATILITY_THRESHOLD_PCT):
        print(f"⚠️ RiskGuardian: High volatility detected for {symbol}. Last changes: {last_candle_change_pct:.2%}, {second_last_candle_change_pct:.2%}, {third_last_candle_change_pct:.2%}")
        return True

    # You can add more sophisticated risk checks here, e.g.,:
    # - Average True Range (ATR) based volatility
    # - Deviation from moving averages
    # - Volume spikes

    return False

