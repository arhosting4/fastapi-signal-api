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
    # Note: pandas_ta returns positive values for bullish patterns and negative for bearish
    # We check for values > 0 for bullish and < 0 for bearish
    engulfing_bull = ta.cdl_engulfing(df['open'], df['high'], df['low'], df['close'])
    hammer = ta.cdl_hammer(df['open'], df['high'], df['low'], df['close'])
    morning_star = ta.cdl_morningstar(df['open'], df['high'], df['low'], df['close'])
    piercing_pattern = ta.cdl_piercing(df['open'], df['high'], df['low'], df['close'])
    doji_star_bull = ta.cdl_dojistar(df['open'], df['high'], df['low'], df['close']) # Doji Star can be bullish or bearish

    # Bearish Reversal Patterns
    # No separate function for bearish engulfing, it's the negative output of cdl_engulfing
    hanging_man = ta.cdl_hangingman(df['open'], df['high'], df['low'], df['close'])
    evening_star = ta.cdl_eveningstar(df['open'], df['high'], df['low'], df['close'])
    dark_cloud_cover = ta.cdl_darkcloudcover(df['open'], df['high'], df['low'], df['close'])
        
    # Check for patterns in the most recent candle (last row of the DataFrame)
    # .iloc[-1] gets the last value of the Series
        
    # Bullish Patterns
    if not engulfing_bull.empty and engulfing_bull.iloc[-1] > 0:
        return {"pattern": "Bullish Engulfing", "confidence": 0.85}
    if not hammer.empty and hammer.iloc[-1] > 0:
        return {"pattern": "Hammer", "confidence": 0.75}
    if not morning_star.empty and morning_star.iloc[-1] > 0:
        return {"pattern": "Morning Star", "confidence": 0.90}
    if not piercing_pattern.empty and piercing_pattern.iloc[-1] > 0:
        return {"pattern": "Piercing Pattern", "confidence": 0.80}
        
    # Bearish Patterns
    if not engulfing_bull.empty and engulfing_bull.iloc[-1] < 0: # Negative value for bearish engulfing
        return {"pattern": "Bearish Engulfing", "confidence": 0.85}
    if not hanging_man.empty and hanging_man.iloc[-1] < 0:
        return {"pattern": "Hanging Man", "confidence": 0.75}
    if not evening_star.empty and evening_star.iloc[-1] < 0:
        return {"pattern": "Evening Star", "confidence": 0.90}
    if not dark_cloud_cover.empty and dark_cloud_cover.iloc[-1] < 0:
        return {"pattern": "Dark Cloud Cover", "confidence": 0.80}
        
    # Doji Star (can be reversal or continuation, needs context)
    if not doji_star_bull.empty and doji_star_bull.iloc[-1] != 0:
        return {"pattern": "Doji Star", "confidence": 0.60} # Lower confidence as it's ambiguous alone

    return {"pattern": "No Specific Pattern", "confidence": 0.50}

