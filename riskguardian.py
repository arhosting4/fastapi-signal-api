# filename: riskguardian.py

from typing import Dict

import numpy as np
import pandas as pd

# مقامی امپورٹس
# مستقبل میں، یہ سیٹنگز config.py سے آ سکتی ہیں
# from config import strategy_settings

# --- مستقل اقدار ---
ATR_LENGTH = 14
# یہ اقدار اثاثے کی قیمت کا فیصد ہیں
VOLATILITY_THRESHOLD_HIGH = 0.005  # 0.5%
VOLATILITY_THRESHOLD_MODERATE = 0.002  # 0.2%

def _calculate_atr(df: pd.DataFrame, period: int) -> pd.Series:
    """
    Average True Range (ATR) کا حساب لگاتا ہے۔
    یہ فنکشن ان پٹ ڈیٹا فریم کی ایک کاپی پر کام کرتا ہے۔
    """
    df_copy = df.copy()
    high, low, close = df_copy['high'], df_copy['low'], df_copy['close']
    
    # True Range (TR) کا حساب
    df_copy['h-l'] = high - low
    df_copy['h-pc'] = abs(high - close.shift(1))
    df_copy['l-pc'] = abs(low - close.shift(1))
    
    tr = df_copy[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    
    # Exponential Moving Average (EMA) کا استعمال کرتے ہوئے ATR کا حساب
    atr = tr.ewm(span=period, adjust=False).mean()
    return atr

def check_risk(df: pd.DataFrame) -> Dict[str, str]:
    """
    مارکیٹ کے اتار چڑھاؤ (volatility) کی بنیاد پر رسک کا اندازہ لگاتا ہے۔
    
    Args:
        df (pd.DataFrame): کینڈل اسٹک ڈیٹا۔
        
    Returns:
        Dict[str, str]: ایک ڈکشنری جس میں رسک کی 'status' اور اس کی 'reason' ہو۔
    """
    if len(df) < ATR_LENGTH + 1:
        return {"status": "Normal", "reason": "رسک کی تشخیص کے لیے ناکافی ڈیٹا۔"}

    # ATR کا حساب لگائیں
    atr = _calculate_atr(df, ATR_LENGTH)

    if atr.empty or pd.isna(atr.iloc[-1]):
        return {"status": "Normal", "reason": "ATR کا حساب نہیں لگایا جا سکا"}
    
    current_atr = atr.iloc[-1]
    # حالیہ 20 کینڈلز کی اوسط قیمت
    avg_close = df['close'].iloc[-20:].mean()
    
    if avg_close == 0:
        return {"status": "Normal", "reason": "قیمت کا ڈیٹا صفر ہے، رسک کا اندازہ نہیں لگایا جا سکتا۔"}

    # متحرک حدوں کا حساب لگائیں
    high_vol_threshold = VOLATILITY_THRESHOLD_HIGH * avg_close
    moderate_vol_threshold = VOLATILITY_THRESHOLD_MODERATE * avg_close

    # رسک کی سطح کا تعین کریں
    if current_atr > high_vol_threshold:
        return {"status": "High", "reason": f"زیادہ اتار چڑھاؤ (ATR: {current_atr:.4f})"}
    elif current_atr > moderate_vol_threshold:
        return {"status": "Moderate", "reason": f"درمیانہ اتار چڑھاؤ (ATR: {current_atr:.4f})"}

    return {"status": "Normal", "reason": "مارکیٹ کے حالات مستحکم ہیں۔"}

def get_dynamic_atr_multiplier(risk_status: str) -> float:
    """
    رسک کی حالت کی بنیاد پر ATR ضرب کا تعین کرتا ہے۔
    (یہ فنکشن فی الحال استعمال نہیں ہو رہا، لیکن مستقبل میں متحرک SL کے لیے مفید ہو سکتا ہے)
    """
    if risk_status == "High":
        return 1.5
    if risk_status == "Moderate":
        return 1.8
    return 2.0
    
