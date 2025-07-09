# src/agents/riskguardian.py
import pandas as pd
import pandas_ta as ta
import numpy as np

def check_risk(candles: list) -> dict:
    """
    Performs a comprehensive risk check based on volatility, recent price action,
    and potential liquidity issues.

    Parameters:
        candles (list): List of OHLC candles (oldest to newest).

    Returns:
        dict: Risk status ("Normal", "Moderate", "High") and a reason.
    """
    if not candles or len(candles) < 30: # Need enough data for ATR and other checks
        return {"status": "Normal", "reason": "Insufficient data for detailed risk assessment."}

    df = pd.DataFrame(candles)
    df['open'] = pd.to_numeric(df['open'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])
    df['volume'] = pd.to_numeric(df['volume'])

    # --- Volatility Check (using ATR - Average True Range) ---
    # ATR measures market volatility. Higher ATR means higher volatility.
    atr = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    if atr.empty or pd.isna(atr.iloc[-1]):
        current_atr = 0.0
    else:
        current_atr = atr.iloc[-1]

    avg_close = df['close'].iloc[-5:].mean() # Average of last 5 closing prices
    
    # Define a volatility threshold as a percentage of average price
    # This threshold might need tuning based on asset type (forex, stocks, crypto)
    volatility_threshold_high = 0.005 * avg_close # e.g., 0.5% of avg price
    volatility_threshold_moderate = 0.002 * avg_close # e.g., 0.2% of avg price

    risk_status = "Normal"
    risk_reason = "Market conditions appear stable."

    if current_atr > volatility_threshold_high:
        risk_status = "High"
        risk_reason = f"High volatility detected (ATR: {current_atr:.4f}). Consider caution."
    elif current_atr > volatility_threshold_moderate:
        risk_status = "Moderate"
        risk_reason = f"Moderate volatility detected (ATR: {current_atr:.4f}). Be aware of price swings."

    # --- Recent Price Action Check (Sharp Moves) ---
    # Check for sudden large candles that might indicate instability
    if len(df) >= 2:
        last_candle_range = abs(df['high'].iloc[-1] - df['low'].iloc[-1])
        prev_candle_range = abs(df['high'].iloc[-2] - df['low'].iloc[-2])
        
        # Compare current candle range to average candle range
        # Ensure there are enough candles for mean calculation
        if len(df) >= 10:
            avg_candle_range = (df['high'] - df['low']).iloc[-10:-2].mean() # Avg of last 8 candles
        else:
            avg_candle_range = (df['high'] - df['low']).mean() # Fallback for less data
        
        if not pd.isna(avg_candle_range) and last_candle_range > (2 * avg_candle_range):
            risk_status = "High"
            risk_reason = "Recent candle shows extreme price movement. High risk."
        elif not pd.isna(avg_candle_range) and last_candle_range > (1.5 * avg_candle_range):
            if risk_status == "Normal": # Only upgrade to moderate if not already high
                risk_status = "Moderate"
                risk_reason = "Recent candle shows significant price movement. Moderate risk."

    # --- Liquidity Check (Volume) ---
    # Very low volume might indicate illiquid market, leading to high slippage
    if not df['volume'].empty and len(df['volume']) >= 10: # Ensure enough volume data
        avg_volume = df['volume'].iloc[-10:].mean()
        if avg_volume > 0 and df['volume'].iloc[-1] < avg_volume * 0.2: # Current volume less than 20% of average
            if risk_status == "Normal":
                risk_status = "Moderate"
                risk_reason = "Low trading volume detected. Potential for high slippage."
            elif risk_status == "High":
                risk_reason += " Also, very low trading volume."
            else:
                risk_reason += " Also, low trading volume."
    elif not df['volume'].empty and df['volume'].iloc[-1] == 0: # Handle cases with zero volume
        if risk_status == "Normal":
            risk_status = "Moderate"
            risk_reason = "Zero trading volume detected. Market might be illiquid."
        elif risk_status == "High":
            risk_reason += " Also, zero trading volume."
        else:
            risk_reason += " Also, zero trading volume."


    return {"status": risk_status, "reason": risk_reason}

