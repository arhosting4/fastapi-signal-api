import pandas as pd
import pandas_ta as ta

def check_risk(candles: list) -> dict:
    if not candles or len(candles) < 30:
        return {"status": "Normal", "reason": "Insufficient data for risk assessment."}

    df = pd.DataFrame(candles)
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.fillna(0, inplace=True)

    atr = ta.atr(df['high'], df['low'], df['close'], length=14)
    if atr is None or atr.empty or pd.isna(atr.iloc[-1]):
        return {"status": "Normal", "reason": "Could not calculate ATR."}
    
    current_atr = atr.iloc[-1]
    avg_close = df['close'].iloc[-20:].mean()
    if avg_close == 0:
        return {"status": "Normal", "reason": "Price data is zero."}

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

    return {"status": risk_status, "reason": risk_reason}

def get_dynamic_atr_multiplier(risk_status: str) -> float:
    if risk_status == "High":
        return 1.5
    if risk_status == "Moderate":
        return 1.8
    return 2.0
    
