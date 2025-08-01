# filename: riskguardian.py

import pandas as pd
import numpy as np
from typing import Dict

ATR_LENGTH = 14

# ★★★ اپ ڈیٹ شدہ فنکشن دستخط ★★★
def check_risk(df: pd.DataFrame) -> Dict[str, str]:
    """
    مارکیٹ کے اتار چڑھاؤ کی بنیاد پر رسک کا اندازہ لگاتا ہے۔
    اب یہ براہ راست پانڈاز ڈیٹا فریم قبول کرتا ہے۔
    """
    if df.empty or len(df) < ATR_LENGTH + 1:
        return {"status": "Normal", "reason": "ناکافی ڈیٹا۔"}

    # اب ڈیٹا فریم بنانے کی ضرورت نہیں
    
    # ATR کا حساب لگانے کے لیے محفوظ طریقہ
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
    
    # صفر سے تقسیم کی خرابی سے بچنے کے لیے چیک
    if avg_close == 0:
        return {"status": "Normal", "reason": "قیمت کا ڈیٹا صفر ہے۔"}

    volatility_threshold_high = 0.005 * avg_close
    volatility_threshold_moderate = 0.002 * avg_close

    if current_atr > volatility_threshold_high:
        return {"status": "High", "reason": f"زیادہ اتار چڑھاؤ (ATR: {current_atr:.4f})"}
    elif current_atr > volatility_threshold_moderate:
        return {"status": "Moderate", "reason": f"درمیانہ اتار چڑھاؤ (ATR: {current_atr:.4f})"}

    return {"status": "Normal", "reason": "مارکیٹ کے حالات مستحکم ہیں۔"}

def get_dynamic_atr_multiplier(risk_status: str) -> float:
    """
    رسک کی حالت کی بنیاد پر ATR ضرب کا تعین کرتا ہے۔
    (یہ فنکشن فی الحال استعمال نہیں ہو رہا، لیکن مستقبل کے لیے مفید ہو سکتا ہے)
    """
    if risk_status == "High": return 1.5
    if risk_status == "Moderate": return 1.8
    return 2.0
    
