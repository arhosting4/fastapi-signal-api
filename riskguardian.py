# filename: riskguardian.py

import pandas as pd
import numpy as np
from typing import Dict

# ★★★ سینٹرل کنفیگ import کرو (config.py) اگر thresholds dynamic چاہئیں ★★★
# from config import RISK_PARAMS
ATR_LENGTH = 14  # یا: ATR_LENGTH = RISK_PARAMS["ATR_LENGTH"]

def check_risk(df: pd.DataFrame) -> Dict[str, str]:
    """
    مارکیٹ کے اتار چڑھاؤ کی بنیاد پر رسک (High/Moderate/Normal) کا اندازہ لگاتا ہے۔
    Input: Pandas DataFrame ('high', 'low', 'close' columns required)
    Output: {"status": "...", "reason": "..."}
    Fail-safe: کبھی incomplete/dirty data پر بھی 'Normal' واپس کرے!
    """
    if df.empty or len(df) < ATR_LENGTH + 1:
        return {"status": "Normal", "reason": "ناکافی ڈیٹا۔"}
    df_copy = df.copy()
    df_copy['h-l'] = df_copy['high'] - df_copy['low']
    df_copy['h-pc'] = np.abs(df_copy['high'] - df_copy['close'].shift())
    df_copy['l-pc'] = np.abs(df_copy['low'] - df_copy['close'].shift())
    tr = df_copy[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    atr = tr.ewm(span=ATR_LENGTH, adjust=False).mean()
    if atr.empty or pd.isna(atr.iloc[-1]):
        return {"status": "Normal", "reason": "ATR کا حساب نہیں لگایا جا سکا"}
    current_atr = atr.iloc[-1]
    avg_close = df['close'].iloc[-20:].mean()
    if avg_close == 0:
        return {"status": "Normal", "reason": "قیمت کا ڈیٹا صفر ہے۔"}
    # threshold values اگر config سے لینا ہو تو یہاں dynamic رکھیں
    volatility_threshold_high = 0.005 * avg_close
    volatility_threshold_moderate = 0.002 * avg_close
    if current_atr > volatility_threshold_high:
        return {"status": "High", "reason": f"زیادہ اتار چڑھاؤ (ATR: {current_atr:.4f})"}
    elif current_atr > volatility_threshold_moderate:
        return {"status": "Moderate", "reason": f"درمیانہ اتار چڑھاؤ (ATR: {current_atr:.4f})"}
    return {"status": "Normal", "reason": "مارکیٹ کے حالات مستحکم ہیں۔"}

def get_dynamic_atr_multiplier(risk_status: str) -> float:
    """
    رسک کی حالت پر مبنی ATR multiplier (future-proof; SL/TP کے حساب کیلئے)
    """
    if risk_status == "High": return 1.5
    if risk_status == "Moderate": return 1.8
    return 2.0
    
