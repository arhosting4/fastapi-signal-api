import pandas as pd
import pandas_ta as ta

def detect_patterns(candles: list) -> dict:
    """
    Detects common candlestick patterns using pandas_ta.

    Parameters:
        candles (list): List of OHLCV data (dicts) from the API.

    Returns:
        dict: Dictionary containing detected pattern and confidence.
    """
    if not candles or len(candles) < 20: # Need enough data for pattern detection
        return {"pattern": "Insufficient Data", "confidence": 0.0}

    # Convert list of dicts to pandas DataFrame
    df = pd.DataFrame(candles)
        
    # Ensure columns are numeric
    df['open'] = pd.to_numeric(df['open'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])
    df['volume'] = pd.to_numeric(df['volume'])

    # --- Candlestick Pattern Detection using pandas_ta ---
    # pandas_ta returns a DataFrame with boolean columns for each pattern
    # We check for common reversal patterns first

    # Bullish Reversal Patterns
    engulfing_bull = ta.cdl_engulfing(df['open'], df['high'], df['low'], df['close'])
    hammer = ta.cdl_hammer(df['open'], df['high'], df['low'], df['close'])
    morning_star = ta.cdl_morningstar(df['open'], df['high'], df['low'], df['close'])
    piercing_pattern = ta.cdl_piercing(df['open'], df['high'], df['low'], df['close'])
    doji_star_bull = ta.cdl_dojistar(df['open'], df['high'], df['low'], df['close']) # Doji Star can be bullish or bearish

    # Bearish Reversal Patterns
    engulfing_bear = ta.cdl_engulfing(df['open'], df['high'], df['low'], df['close']) # Same function, check negative values
    hanging_man = ta.cdl_hangingman(df['open'], df['high'], df['low'], df['close'])
    evening_star = ta.cdl_eveningstar(df['open'], df['high'], df['low'], df['close'])
    dark_cloud_cover = ta.cdl_darkcloudcover(df['open'], df['high'], df['low'], df['close'])

    # Check for patterns in the most recent candle (last row of the DataFrame)
    last_candle_index = df.index[-1]

    # Bullish Patterns
    if engulfing_bull is not None and not engulfing_bull.empty and engulfing_bull.iloc[-1] > 0:
        return {"pattern": "Bullish Engulfing", "confidence": 0.85}
    if hammer is not None and not hammer.empty and hammer.iloc[-1] > 0:
        return {"pattern": "Hammer", "confidence": 0.75}
    if morning_star is not None and not morning_star.empty and morning_star.iloc[-1] > 0:
        return {"pattern": "Morning Star", "confidence": 0.90}
    if piercing_pattern is not None and not piercing_pattern.empty and piercing_pattern.iloc[-1] > 0:
        return {"pattern": "Piercing Pattern", "confidence": 0.80}
        
    # Bearish Patterns
    if engulfing_bear is not None and not engulfing_bear.empty and engulfing_bear.iloc[-1] < 0:
        return {"pattern": "Bearish Engulfing", "confidence": 0.85}
    if hanging_man is not None and not hanging_man.empty and hanging_man.iloc[-1] < 0:
        return {"pattern": "Hanging Man", "confidence": 0.75}
    if evening_star is not None and not evening_star.empty and evening_star.iloc[-1] < 0:
        return {"pattern": "Evening Star", "confidence": 0.90}
    if dark_cloud_cover is not None and not dark_cloud_cover.
    
