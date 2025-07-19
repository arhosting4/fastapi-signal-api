import pandas as pd
import pandas_ta as ta
from typing import Dict, List

def check_risk(candles: List[Dict]) -> Dict:
    """
    رسک کا جامع تجزیہ کرتا ہے اور اتار چڑھاؤ کی بنیاد پر TP/SL کے ضرب کا مشورہ دیتا ہے۔
    """
    if not candles or len(candles) < 30:
        return {
            "status": "Normal", 
            "reason": "Insufficient data for detailed risk assessment.",
            "tp_multiplier": 2.0, # ڈیفالٹ
            "sl_multiplier": 1.0  # ڈیفالٹ
        }

    df = pd.DataFrame(candles)
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.fillna(0, inplace=True)

    # 1. اتار چڑھاؤ کا تجزیہ (ATR)
    atr = ta.atr(df['high'], df['low'], df['close'], length=14)
    if atr is None or atr.empty or pd.isna(atr.iloc[-1]):
        current_atr = 0.0
    else:
        current_atr = atr.iloc[-1]

    avg_close = df['close'].iloc[-20:].mean()
    if avg_close == 0:
        return {
            "status": "Normal", 
            "reason": "Price data is zero, risk cannot be assessed.",
            "tp_multiplier": 2.0,
            "sl_multiplier": 1.0
        }

    # اتار چڑھاؤ کی سطحیں
    volatility_percentage = (current_atr / avg_close) * 100
    
    risk_status = "Normal"
    risk_reason = "Market conditions appear stable."
    tp_multiplier = 2.0  # ڈیفالٹ
    sl_multiplier = 1.0  # ڈیفالٹ

    if volatility_percentage > 0.3: # بہت زیادہ اتار چڑھاؤ (مثلاً 0.3% سے زیادہ)
        risk_status = "High"
        risk_reason = f"High volatility detected (ATR is {volatility_percentage:.2f}% of price)."
        tp_multiplier = 1.5 # جلدی منافع لیں
        sl_multiplier = 1.2 # SL کو تھوڑا دور رکھیں
    elif volatility_percentage > 0.15: # درمیانہ اتار چڑھاؤ
        risk_status = "Moderate"
        risk_reason = f"Moderate volatility detected (ATR is {volatility_percentage:.2f}% of price)."
        tp_multiplier = 2.0 # معیاری
        sl_multiplier = 1.0 # معیاری
    else: # کم اتار چڑھاؤ
        risk_status = "Low"
        risk_reason = f"Low volatility detected (ATR is {volatility_percentage:.2f}% of price)."
        tp_multiplier = 2.5 # بڑا منافع حاصل کرنے کی کوشش کریں
        sl_multiplier = 0.8 # SL کو قریب رکھیں

    # 2. حالیہ تیز حرکت کا تجزیہ (پہلے کی طرح)
    if len(df) >= 10:
        last_candle_range = abs(df['high'].iloc[-1] - df['low'].iloc[-1])
        avg_candle_range = (df['high'] - df['low']).iloc[-10:-2].mean()
        
        if avg_candle_range > 0 and last_candle_range > (2.5 * avg_candle_range):
            risk_status = "High"
            risk_reason = "Recent candle shows extreme price movement. High risk."
            # اگر اچانک اسپائک آئے تو رسک کو مزید سخت کریں
            tp_multiplier = min(tp_multiplier, 1.2)
            sl_multiplier = max(sl_multiplier, 1.3)

    return {
        "status": risk_status, 
        "reason": risk_reason,
        "tp_multiplier": tp_multiplier,
        "sl_multiplier": sl_multiplier
    }
    
