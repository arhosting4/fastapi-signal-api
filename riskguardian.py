import pandas as pd
import pandas_ta as ta
from typing import Dict, List

def check_risk(candles: List[Dict]) -> Dict:
    if not candles or len(candles) < 30:
        return {"status": "Normal", "reason": "Insufficient data.", "tp_multiplier": 2.0, "sl_multiplier": 1.0}
    df = pd.DataFrame(candles)
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.fillna(0, inplace=True)
    atr = ta.atr(df['high'], df['low'], df['close'], length=14)
    if atr is None or atr.empty or pd.isna(atr.iloc[-1]):
        current_atr = 0.0
    else:
        current_atr = atr.iloc[-1]
    avg_close = df['close'].iloc[-20:].mean()
    if avg_close == 0:
        return {"status": "Normal", "reason": "Price is zero.", "tp_multiplier": 2.0, "sl_multiplier": 1.0}
    volatility_percentage = (current_atr / avg_close) * 100
    risk_status, risk_reason = "Normal", "Market stable."
    tp_multiplier, sl_multiplier = 2.0, 1.0
    if volatility_percentage > 0.3:
        risk_status, risk_reason = "High", f"High volatility ({volatility_percentage:.2f}%)."
        tp_multiplier, sl_multiplier = 1.5, 1.2
    elif volatility_percentage > 0.15:
        risk_status, risk_reason = "Moderate", f"Moderate volatility ({volatility_percentage:.2f}%)."
        tp_multiplier, sl_multiplier = 2.0, 1.0
    else:
        risk_status, risk_reason = "Low", f"Low volatility ({volatility_percentage:.2f}%)."
        tp_multiplier, sl_multiplier = 2.5, 0.8
    if len(df) >= 10:
        last_candle_range = abs(df['high'].iloc[-1] - df['low'].iloc[-1])
        avg_candle_range = (df['high'] - df['low']).iloc[-10:-2].mean()
        if avg_candle_range > 0 and last_candle_range > (2.5 * avg_candle_range):
            risk_status = "High"
            risk_reason = "Extreme price movement."
            tp_multiplier = min(tp_multiplier, 1.2)
            sl_multiplier = max(sl_multiplier, 1.3)
    return {"status": risk_status, "reason": risk_reason, "tp_multiplier": tp_multiplier, "sl_multiplier": sl_multiplier}
    
