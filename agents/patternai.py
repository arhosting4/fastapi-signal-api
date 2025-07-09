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
    # We need to call them directly from the ta module and get the last value.

    # Bullish Patterns
    engulfing_bull_series = ta.cdl_engulfing(df['open'], df['high'], df['low'], df['close'])
    engulfing_bull = engulfing_bull_series.iloc[-1] if engulfing_bull_series is not None else 0

    hammer_series = ta.cdl_hammer(df['open'], df['high'], df['low'], df['close'])
    hammer = hammer_series.iloc[-1] if hammer_series is not None else 0

    morning_star_series = ta.cdl_morningstar(df['open'], df['high'], df['low'], df['close'])
    morning_star = morning_star_series.iloc[-1] if morning_star_series is not None else 0

    piercing_series = ta.cdl_piercing(df['open'], df['high'], df['low'], df['close'])
    piercing = piercing_series.iloc[-1] if piercing_series is not None else 0

    three_white_soldiers_series = ta.cdl_3whitesoldiers(df['open'], df['high'], df['low'], df['close'])
    three_white_soldiers = three_white_soldiers_series.iloc[-1] if three_white_soldiers_series is not None else 0

    # Bearish Patterns
    dark_cloud_cover_series = ta.cdl_darkcloudcover(df['open'], df['high'], df['low'], df['close'])
    dark_cloud_cover = dark_cloud_cover_series.iloc[-1] if dark_cloud_cover_series is not None else 0

    hanging_man_series = ta.cdl_hangingman(df['open'], df['high'], df['low'], df['close'])
    hanging_man = hanging_man_series.iloc[-1] if hanging_man_series is not None else 0

    shooting_star_series = ta.cdl_shootingstar(df['open'], df['high'], df['low'], df['close'])
    shooting_star = shooting_star_series.iloc[-1] if shooting_star_series is not None else 0

    evening_star_series = ta.cdl_eveningstar(df['open'], df['high'], df['low'], df['close'])
    evening_star = evening_star_series.iloc[-1] if evening_star_series is not None else 0

    three_black_crows_series = ta.cdl_3blackcrows(df['open'], df['high'], df['low'], df['close'])
    three_black_crows = three_black_crows_series.iloc[-1] if three_black_crows_series is not None else 0


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

