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
    df['open'] = pd.to_numeric(df['open'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])

    # --- Candlestick Pattern Detection ---
    # pandas_ta returns 0 for no pattern, 100 for bullish, -100 for bearish

    # Bullish Patterns
    engulfing_bull = ta.cdl_engulfing(df['open'], df['high'], df['low'], df['close'])
    hammer = ta.cdl_hammer(df['open'], df['high'], df['low'], df['close'])
    morning_star = ta.cdl_morningstar(df['open'], df['high'], df['low'], df['close'])
    piercing = ta.cdl_piercing(df['open'], df['high'], df['low'], df['close'])
    three_white_soldiers = ta.cdl_3whitesoldiers(df['open'], df['high'], df['low'], df['close'])

    # Bearish Patterns
    dark_cloud_cover = ta.cdl_darkcloudcover(df['open'], df['high'], df['low'], df['close'])
    hanging_man = ta.cdl_hangingman(df['open'], df['high'], df['low'], df['close'])
    shooting_star = ta.cdl_shootingstar(df['open'], df['high'], df['low'], df['close'])
    evening_star = ta.cdl_eveningstar(df['open'], df['high'], df['low'], df['close'])
    three_black_crows = ta.cdl_3blackcrows(df['open'], df['high'], df['low'], df['close'])

    # Check for patterns in the latest candle
    # Prioritize stronger or more common patterns

    # Bearish Checks
    if not dark_cloud_cover.empty and dark_cloud_cover.iloc[-1] < 0:
        return {"pattern": "Dark Cloud Cover", "type": "bearish"}
    if not hanging_man.empty and hanging_man.iloc[-1] < 0:
        return {"pattern": "Hanging Man", "type": "bearish"}
    if not shooting_star.empty and shooting_star.iloc[-1] < 0:
        return {"pattern": "Shooting Star", "type": "bearish"}
    if not evening_star.empty and evening_star.iloc[-1] < 0:
        return {"pattern": "Evening Star", "type": "bearish"}
    if not three_black_crows.empty and three_black_crows.iloc[-1] < 0:
        return {"pattern": "Three Black Crows", "type": "bearish"}

    # Bullish Checks
    if not engulfing_bull.empty and engulfing_bull.iloc[-1] > 0:
        return {"pattern": "Bullish Engulfing", "type": "bullish"}
    if not hammer.empty and hammer.iloc[-1] > 0:
        return {"pattern": "Hammer", "type": "bullish"}
    if not morning_star.empty and morning_star.iloc[-1] > 0:
        return {"pattern": "Morning Star", "type": "bullish"}
    if not piercing.empty and piercing.iloc[-1] > 0:
        return {"pattern": "Piercing Pattern", "type": "bullish"}
    if not three_white_soldiers.empty and three_white_soldiers.iloc[-1] > 0:
        return {"pattern": "Three White Soldiers", "type": "bullish"}

    return {"pattern": "No Specific Pattern", "type": "neutral"}

