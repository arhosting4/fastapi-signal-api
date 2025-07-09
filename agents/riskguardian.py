import pandas as pd
import pandas_ta as ta

def check_risk(symbol: str, candles: list) -> bool:
    """
    Checks market risk based on volatility using Average True Range (ATR).
    Returns True if volatility is too high, indicating risky trading conditions.

    Parameters:
        symbol (str): The trading pair symbol.
        candles (list): List of OHLC candles.

    Returns:
        bool: True if market risk is high, False otherwise.
    """
    if not candles or len(candles) < 20: # ATR(14) needs at least 14 periods, let's use 20 for safety
        return False # Not enough data to assess risk, assume low risk for now

    df = pd.DataFrame(candles)
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])

    # Calculate ATR (Average True Range)
    # Default length is 14
    atr = ta.atr(df['high'], df['low'], df['close'], length=14)

    if atr.empty:
        return False # Could not calculate ATR, assume low risk

    latest_atr = atr.iloc[-1]
    average_close = df['close'].mean() # Average price over the period

    # Define a dynamic risk threshold based on average price
    # For example, if ATR is more than 1% of the average price, consider it high risk.
    # This threshold might need tuning based on asset class (stocks vs. forex)
    risk_threshold_percentage = 0.01 # 1% of average price
    risk_threshold_value = risk_threshold_percentage * average_close

    print(f"DEBUG: Risk Check for {symbol}: Latest ATR={latest_atr:.4f}, Avg Close={average_close:.4f}, Threshold={risk_threshold_value:.4f}")

    if latest_atr > risk_threshold_value:
        print(f"⚠️ High risk detected for {symbol}: ATR ({latest_atr:.4f}) > Threshold ({risk_threshold_value:.4f})")
        return True
    else:
        return False
        
