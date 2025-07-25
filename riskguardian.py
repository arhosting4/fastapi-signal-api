# filename: riskguardian.py

import pandas as pd
import pandas_ta as ta
from typing import List, Dict

# ==============================================================================
# کنفیگریشن پیرامیٹرز براہ راست یہاں شامل کر دیے گئے ہیں
# ==============================================================================
ATR_LENGTH = 14
ATR_MULTIPLIER_HIGH_RISK = 1.5
ATR_MULTIPLIER_MODERATE_RISK = 1.8
ATR_MULTIPLIER_NORMAL_RISK = 2.0
# ==============================================================================

def check_risk(candles: List[Dict]) -> Dict[str, str]:
    """
    مارکیٹ کے اتار چڑھاؤ کی بنیاد پر رسک کا اندازہ لگاتا ہے۔
    """
    if not candles or len(candles) < 30:
        return {"status": "Normal", "reason": "ناکافی ڈیٹا۔"}

    # --- اہم تبدیلی: اب یہ پہلے سے ہی ڈکشنری ہے ---
    df = pd.DataFrame(candles)
    
    for col in ['high', 'low', 'close']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df.dropna(inplace=True)
    if len(df) < 14:
        return {"status": "Normal", "reason": "ناکافی ڈیٹا۔"}

    atr = ta.atr(df['high'], df['low'], df['close'], length=ATR_LENGTH)
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

def get_dynamic_atr_multiplier(risk_status: str) -> float:
    """
    رسک کی سطح کی بنیاد پر ATR ضرب کو متحرک طور پر ایڈجسٹ کرتا ہے۔
    """
    if risk_status == "High":
        return ATR_MULTIPLIER_HIGH_RISK
    if risk_status == "Moderate":
        return ATR_MULTIPLIER_MODERATE_RISK
    return ATR_MULTIPLIER_NORMAL_RISK
    
