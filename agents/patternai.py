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
    # We need to call them as methods on the DataFrame and then check the last value.

    # Bullish Patterns
    df.ta.cdl_engulfing(append=True)
    engulfing_bull = df["CDL_ENGULFING"].iloc[-1] if "CDL_ENGULFING" in df.columns else 0

    df.ta.cdl_hammer(append=True)
    hammer = df["CDL_HAMMER"].iloc[-1] if "CDL_HAMMER" in df.columns else 0

    df.ta.cdl_morningstar(append=True)
    morning_star = df["CDL_MORNINGSTAR"].iloc[-1] if "CDL_MORNINGSTAR" in df.columns else 0

    df.ta.cdl_piercing(append=True)
    piercing = df["CDL_PIERCING"].iloc[-1] if "CDL_PIERCING" in df.columns else 0

    df.ta.cdl_3whitesoldiers(append=True)
    three_white_soldiers = df["CDL_3WHITESOLDIERS"].iloc[-1] if "CDL_3WHITESOLDIERS" in df.columns else 0

    # Bearish Patterns
    df.ta.cdl_darkcloudcover(append=True)
    dark_cloud_cover = df["CDL_DARKCLOUDCOVER"].iloc[-1] if "CDL_DARKCLOUDCOVER" in df.columns else 0

    df.ta.cdl_hangingman(append=True)
    hanging_man = df["CDL_HANGINGMAN"].iloc[-1] if "CDL_HANGINGMAN" in df.columns else 0

    df.ta.cdl_shootingstar(append=True)
    shooting_star = df["CDL_SHOOTINGSTAR"].iloc[-1] if "CDL_SHOOTINGSTAR" in df.columns else 0

    df.ta.cdl_eveningstar(append=True)
    evening_star = df["CDL_EVENINGSTAR"].iloc[-1] if "CDL_EVENINGSTAR" in df.columns else 0

    df.ta.cdl_3blackcrows(append=True)
    three_black_crows = df["CDL_3BLACKCROWS"].iloc[-1] if "CDL_3BLACKCROWS" in df.columns else 0


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
    
