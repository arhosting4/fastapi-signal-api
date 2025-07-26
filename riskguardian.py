# filename: riskguardian.py

import pandas as pd
import numpy as np # numpy کو امپورٹ کریں گے
from typing import List, Dict

# ==============================================================================
# کنفیگریشن پیرامیٹرز
# ==============================================================================
ATR_LENGTH = 14
# (ضرب کی اب ضرورت نہیں کیونکہ ہم رسک کی بنیاد پر TP/SL کو ایڈجسٹ نہیں کر رہے)
# ==============================================================================

def check_risk(candles: List[Dict]) -> Dict[str, str]:
    """
    مارکیٹ کے اتار چڑھاؤ کی بنیاد پر رسک کا اندازہ لگاتا ہے۔
    ★★★ اب یہ pandas_ta استعمال نہیں کرتا ★★★
    """
    if not candles or len(candles) < 30:
        return {"status": "Normal", "reason": "ناکافی ڈیٹا۔"}

    df = pd.DataFrame(candles)
    
    for col in ['high', 'low', 'close']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df.dropna(inplace=True)
    if len(df) < 14:
        return {"status": "Normal", "reason": "ناکافی ڈیٹا۔"}

    # ATR کا حساب لگانے کے لیے محفوظ طریقہ
    df['h-l'] = df['high'] - df['low']
    df['h-pc'] = np.abs(df['high'] - df['close'].shift())
    df['l-pc'] = np.abs(df['low'] - df['close'].shift())
    tr = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    atr = tr.rolling(window=ATR_LENGTH).mean()

    if atr is None or atr.empty or pd.isna(atr.iloc[-1]):
        return {"status": "Normal", "reason": "ATR کا حساب نہیں لگایا جا سکا"}
    
    current_atr = atr.iloc[-1]
    avg_close = df['close'].iloc[-20:].mean()
    if avg_close == 0:
        return {"status": "Normal", "reason": "قیمت کا ڈیٹا صفر ہے۔"}

    volatility_threshold_high = 0.005 * avg_close
    volatility_threshold_moderate = 0.002 * avg_close

    if current_atr > volatility_threshold_high:
        return {"status": "High", "reason": f"زیادہ اتار چڑھاؤ (ATR: {current_atr:.4f})"}
    elif current_atr > volatility_threshold_moderate:
        return {"status": "Moderate", "reason": f"درمیانہ اتار چڑھاؤ (ATR: {current_atr:.4f})"}

    return {"status": "Normal", "reason": "مارکیٹ کے حالات مستحکم ہیں۔"}

# اس فنکشن کی اب ضرورت نہیں، لیکن ہم اسے رکھ سکتے ہیں تاکہ کوئی امپورٹ ایرر نہ آئے۔
def get_dynamic_atr_multiplier(risk_status: str) -> float:
    """رسک کی سطح کی بنیاد پر ATR ضرب کو متحرک طور پر ایڈجسٹ کرتا ہے۔"""
    if risk_status == "High":
        return 1.5
    if risk_status == "Moderate":
        return 1.8
    return 2.0
        
