# src/agents/patternai.py
import pandas_ta as ta
import pandas as pd

def detect_patterns(candles: list) -> dict:
    """
    Detects various candlestick patterns using pandas_ta.

    Parameters:
        candles (list): List of OHLC candles (oldest to newest).

    Returns:
        dict: A dictionary containing detected pattern and its type (bullish/bearish).
    """
    if not candles or len(candles) < 20: # Need enough data for some patterns
        return {"pattern": "Insufficient Data", "type": "neutral"}

    # Convert list of dicts to pandas DataFrame
    df = pd.DataFrame(candles)
    
    # Ensure columns are numeric and correctly named for pandas_ta
    df["open"] = pd.to_numeric(df["open"])
    df["high"] = pd.to_numeric(df["high"])
    df["low"] = pd.to_numeric(df["low"])
    df["close"] = pd.to_numeric(df["close"])

    # --- Candlestick Pattern Detection ---
    # pandas_ta returns 0 for no pattern, 100 for bullish, -100 for bearish
    # We need to call them using the cdl_pattern wrapper and then check the last value.

    # Bullish Patterns
    engulfing_bull = ta.cdl_engulfing(open=df["open"], high=df["high"], low=df["low"], close=df["close"]).iloc[-1]
    hammer = ta.cdl_hammer(open=df["open"], high=df["high"], low=df["low"], close=df["close"]).iloc[-1]
    morning_star = ta.cdl_morningstar(open=df["open"], high=df["high"], low=df["low"], close=df["close"]).iloc[-1]
    piercing = ta.cdl_piercing(open=df["open"], high=df["high"], low=df["low"], close=df["close"]).iloc[-1]
    three_white_soldiers = ta.cdl_3whitesoldiers(open=df["open"], high=df["high"], low=df["low"], close=df["close"]).iloc[-1]

    # Bearish Patterns
    dark_cloud_cover = ta.cdl_darkcloudcover(open=df["open"], high=df["high"], low=df["low"], close=df["close"]).iloc[-1]
    hanging_man = ta.cdl_hangingman(open=df["open"], high=df["high"], low=df["low"], close=df["close"]).iloc[-1]
    shooting_star = ta.cdl_shootingstar(open=df["open"], high=df["high"], low=df["low"], close=df["close"]).iloc[-1]
    evening_star = ta.cdl_eveningstar(open=df["open"], high=df["high"], low=df["low"], close=df["close"]).iloc[-1]
    three_black_crows = ta.cdl_3blackcrows(open=df["open"], high=df["high"], low=df["low"], close=df["close"]).iloc[-1]


    # Check for patterns in the latest candle
    # Prioritize stronger or more common patterns

    # Bearish Checks
    if dark_cloud_cover < 0:
        return {"pattern": "Dark Cloud Cover", "type": "bearish"}
    if hanging_man < 0:
        return {"pattern": "Hanging Man", "type": "bearish"}
    if shooting_star < 0:
        return {"pattern": "Shooting Star", "type": "bearish"}
    if evening_star < 0:
        return {"pattern": "Evening Star", "type": "bearish"}
    if three_black_crows < 0:
        return {"pattern": "Three Black Crows", "type": "bearish"}

    # Bullish Checks
    if engulfing_bull > 0:
        return {"pattern": "Bullish Engulfing", "type": "bullish"}
    if hammer > 0:
        return {"pattern": "Hammer", "type": "bullish"}
    if morning_star > 0:
        return {"pattern": "Morning Star", "type": "bullish"}
    if piercing > 0:
        return {"pattern": "Piercing Pattern", "type": "bullish"}
    if three_white_soldiers > 0:
        return {"pattern": "Three White Soldiers", "type": "bullish"}

    return {"pattern": "No Specific Pattern", "type": "neutral"}
    
