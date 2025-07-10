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

    # Helper function to safely get pattern value
    def get_pattern_value(pattern_series):
        # Ensure pattern_series is a pandas Series and not empty
        if isinstance(pattern_series, pd.Series) and not pattern_series.empty:
            # Get the last value and convert it to a float, handling potential NaNs
            value = pattern_series.iloc[-1]
            if pd.isna(value):
                return 0.0 # Return 0 if the last value is NaN
            return float(value)
        return 0.0 # Default to 0.0 if no pattern or empty series

    # Bullish Patterns
    engulfing_bull = get_pattern_value(ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"], name="engulfing"))
    hammer = get_pattern_value(ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"], name="hammer"))
    morning_star = get_pattern_value(ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"], name="morningstar"))
    piercing = get_pattern_value(ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"], name="piercing"))
    three_white_soldiers = get_pattern_value(ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"], name="3whitesoldiers"))

    # Bearish Patterns
    dark_cloud_cover = get_pattern_value(ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"], name="darkcloudcover"))
    hanging_man = get_pattern_value(ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"], name="hangingman"))
    shooting_star = get_pattern_value(ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"], name="shootingstar"))
    evening_star = get_pattern_value(ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"], name="eveningstar"))
    three_black_crows = get_pattern_value(ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"], name="3blackcrows"))


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
    
