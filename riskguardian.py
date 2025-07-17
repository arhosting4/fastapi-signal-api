import pandas as pd
import pandas_ta as ta
import numpy as np

def check_risk(candles: list) -> dict:
    """
    Performs a comprehensive risk check based on volatility, recent price action,
    and potential liquidity issues.
    """
    if not candles or len(candles) < 30:
        return {"status": "Normal", "reason": "Insufficient data for detailed risk assessment."}

    df = pd.DataFrame(candles)
    
    # --- اہم ترین تبدیلی: تمام کالمز کو numeric بنائیں ---
    # errors='coerce' کسی بھی غیر عددی ویلیو کو NaN (Not a Number) میں تبدیل کر دے گا
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # اگر کوئی اہم ویلیو NaN ہو جائے تو اسے 0 سے بھر دیں
    df.fillna(0, inplace=True)

    # --- Volatility Check (using ATR - Average True Range) ---
    atr = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    if atr is None or atr.empty or pd.isna(atr.iloc[-1]):
        current_atr = 0.0
    else:
        current_atr = atr.iloc[-1]

    # اگر avg_close 0 ہو تو تقسیم کے ایرر سے بچیں
    avg_close = df['close'].iloc[-20:].mean()
    if avg_close == 0:
        return {"status": "Normal", "reason": "Price data is zero, risk cannot be assessed."}

    volatility_threshold_high = 0.005 * avg_close
    volatility_threshold_moderate = 0.002 * avg_close

    risk_status = "Normal"
    risk_reason = "Market conditions appear stable."

    if current_atr > volatility_threshold_high:
        risk_status = "High"
        risk_reason = f"High volatility detected (ATR: {current_atr:.4f})."
    elif current_atr > volatility_threshold_moderate:
        risk_status = "Moderate"
        risk_reason = f"Moderate volatility detected (ATR: {current_atr:.4f})."

    # --- Recent Price Action Check (Sharp Moves) ---
    if len(df) >= 10:
        last_candle_range = abs(df['high'].iloc[-1] - df['low'].iloc[-1])
        avg_candle_range = (df['high'] - df['low']).iloc[-10:-2].mean()
        
        if avg_candle_range > 0: # صفر سے تقسیم کے ایرر سے بچیں
            if last_candle_range > (2.5 * avg_candle_range):
                risk_status = "High"
                risk_reason = "Recent candle shows extreme price movement. High risk."
            elif last_candle_range > (1.7 * avg_candle_range) and risk_status == "Normal":
                risk_status = "Moderate"
                risk_reason = "Recent candle shows significant price movement. Moderate risk."

    # --- Liquidity Check (Volume) ---
    if 'volume' in df.columns and len(df['volume']) >= 10:
        avg_volume = df['volume'].iloc[-10:].mean()
        if avg_volume > 0 and df['volume'].iloc[-1] < avg_volume * 0.2:
            if risk_status == "Normal":
                risk_status = "Moderate"
                risk_reason = "Low trading volume detected. Potential for high slippage."
            else: # اگر پہلے سے ہی کوئی رسک ہے تو اس میں اضافہ کریں
                risk_reason += " Additionally, low trading volume detected."

    return {"status": risk_status, "reason": risk_reason}
    
