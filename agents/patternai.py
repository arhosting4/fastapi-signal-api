import pandas as pd
import pandas_ta as ta

def detect_patterns(symbol: str, tf: str, candles: list) -> dict:
    """
    Detects common candlestick patterns using pandas_ta.

    Parameters:
        symbol (str): Trading pair symbol.
        tf (str): Timeframe.
        candles (list): List of OHLC candles.

    Returns:
        dict: A dictionary containing detected pattern and its confidence.
              Returns "No Specific Pattern" if no significant pattern is found.
    """
    if not candles or len(candles) < 30: # Need enough data for patterns
        return {"pattern": "No Specific Pattern", "confidence": 0.5}

    # Convert list of dicts to pandas DataFrame
    df = pd.DataFrame(candles)
    # Ensure columns are numeric and correctly named for pandas_ta
    df['open'] = pd.to_numeric(df['open'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])
    df['volume'] = pd.to_numeric(df['volume'])

    # --- Candlestick Pattern Detection using pandas_ta ---
    # pandas_ta has many candlestick patterns. We'll check for a few common ones.
    # The functions return a Series with 100 for bullish, -100 for bearish, 0 for no pattern.

    # Bullish Patterns
    engulfing_bull = ta.cdl_engulfing(df['open'], df['high'], df['low'], df['close'])
    hammer = ta.cdl_hammer(df['open'], df['high'], df['low'], df['close'])
    morning_star = ta.cdl_morningstar(df['open'], df['high'], df['low'], df['close'])
    piercing = ta.cdl_piercing(df['open'], df['high'], df['low'], df['close'])

    # Bearish Patterns
    engulfing_bear = ta.cdl_engulfing(df['open'], df['high'], df['low'], df['close']) * -1 # Engulfing is bidirectional
    hanging_man = ta.cdl_hangingman(df['open'], df['high'], df['low'], df['close'])
    evening_star = ta.cdl_eveningstar(df['open'], df['high'], df['low'], df['close'])
    dark_cloud_cover = ta.cdl_darkcloudcover(df['open'], df['high'], df['low'], df['close'])

    # Get the latest pattern values
    latest_engulfing_bull = engulfing_bull.iloc[-1]
    latest_hammer = hammer.iloc[-1]
    latest_morning_star = morning_star.iloc[-1]
    latest_piercing = piercing.iloc[-1]

    latest_engulfing_bear = engulfing_bear.iloc[-1]
    latest_hanging_man = hanging_man.iloc[-1]
    latest_evening_star = evening_star.iloc[-1]
    latest_dark_cloud_cover = dark_cloud_cover.iloc[-1]

    # Prioritize patterns (you can adjust this order based on importance)
    # Bullish patterns
    if latest_engulfing_bull == 100:
        return {"pattern": "Bullish Engulfing", "confidence": 0.85}
    if latest_morning_star == 100:
        return {"pattern": "Morning Star", "confidence": 0.80}
    if latest_piercing == 100:
        return {"pattern": "Piercing Pattern", "confidence": 0.75}
    if latest_hammer == 100:
        return {"pattern": "Hammer", "confidence": 0.70}

    # Bearish patterns
    if latest_engulfing_bear == -100:
        return {"pattern": "Bearish Engulfing", "confidence": 0.85}
    if latest_evening_star == -100:
        return {"pattern": "Evening Star", "confidence": 0.80}
    if latest_dark_cloud_cover == -100:
        return {"pattern": "Dark Cloud Cover", "confidence": 0.75}
    if latest_hanging_man == -100:
        return {"pattern": "Hanging Man", "confidence": 0.70}

    return {"pattern": "No Specific Pattern", "confidence": 0.5}
    
