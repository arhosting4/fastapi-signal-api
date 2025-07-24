# filename: riskguardian.py
import pandas as pd
import pandas_ta as ta
from typing import List, Dict

import config
from schemas import Candle

def check_risk(candles: List[Candle]) -> Dict[str, str]:
    """مارکیٹ کے اتار چڑھاؤ کی بنیاد پر رسک کا اندازہ لگاتا ہے۔"""
    if len(candles) < config.ATR_LENGTH:
        return {"status": "Normal", "reason": "رسک کے جائزے کے لیے ناکافی ڈیٹا۔"}

    df = pd.DataFrame([c.dict() for c in candles])
    
    atr = ta.atr(df['high'], df['low'], df['close'], length=config.ATR_LENGTH)
    if atr is None or atr.empty or pd.isna(atr.iloc[-1]):
        return {"status": "Normal", "reason": "ATR کا حساب نہیں لگایا جا سکا۔"}
    
    current_atr = atr.iloc[-1]
    avg_close = df['close'].iloc[-20:].mean()
    if avg_close == 0:
        return {"status": "Normal", "reason": "قیمت کا ڈیٹا صفر ہے، رسک کا اندازہ نہیں لگایا جا سکتا۔"}

    # رسک کی حدوں کی وضاحت
    volatility_percentage = (current_atr / avg_close) * 100
    
    risk_status = "Normal"
    risk_reason = f"معمول کا اتار چڑھاؤ ({volatility_percentage:.2f}%)۔"

    if volatility_percentage > 0.5: # 0.5% سے زیادہ اتار چڑھاؤ زیادہ رسک ہے
        risk_status = "High"
        risk_reason = f"زیادہ اتار چڑھاؤ کا پتہ چلا ({volatility_percentage:.2f}%)۔"
    elif volatility_percentage > 0.2: # 0.2% سے زیادہ درمیانہ رسک ہے
        risk_status = "Moderate"
        risk_reason = f"درمیانہ اتار چڑھاؤ کا پتہ چلا ({volatility_percentage:.2f}%)۔"

    return {"status": risk_status, "reason": risk_reason}

def get_dynamic_atr_multiplier(risk_status: str) -> float:
    """رسک کی سطح کی بنیاد پر ATR ضرب کو متحرک طور پر ایڈجسٹ کرتا ہے۔"""
    if risk_status == "High":
        return config.ATR_MULTIPLIER_HIGH_RISK
    if risk_status == "Moderate":
        return config.ATR_MULTIPLIER_MODERATE_RISK
    return config.ATR_MULTIPLIER_NORMAL_RISK
    
