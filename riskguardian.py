# filename: riskguardian.py

import pandas as pd
import pandas_ta as ta

def check_risk(candles: list) -> dict:
    """
    مارکیٹ کے اتار چڑھاؤ (volatility) کی بنیاد پر رسک کا اندازہ لگاتا ہے۔
    یہ اب 'volume' کالم کی عدم موجودگی کو شائستگی سے سنبھالتا ہے۔
    """
    if not candles or len(candles) < 30:
        return {"status": "Normal", "reason": "Insufficient data for risk assessment."}

    df = pd.DataFrame(candles)
    
    # --- اہم اور حتمی اصلاح: صرف ان کالموں کو پروسیس کریں جو DataFrame میں موجود ہیں ---
    expected_cols = ['open', 'high', 'low', 'close', 'volume']
    available_cols = [col for col in expected_cols if col in df.columns]

    # صرف دستیاب عددی کالموں کو تبدیل کریں
    for col in available_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # اگر کوئی کالم تبدیل کرنے کے بعد خالی ہو جائے تو اسے صفر سے بھر دیں
    df.fillna(0, inplace=True)

    # ATR کیلکولیشن کے لیے 'high', 'low', 'close' لازمی ہیں
    required_atr_cols = ['high', 'low', 'close']
    if not all(col in df.columns for col in required_atr_cols):
        return {"status": "Normal", "reason": "Essential price data (HLC) missing for ATR calculation."}

    atr = ta.atr(df['high'], df['low'], df['close'], length=14)
    if atr is None or atr.empty or pd.isna(atr.iloc[-1]):
        return {"status": "Normal", "reason": "Could not calculate ATR."}
    
    current_atr = atr.iloc[-1]
    avg_close = df['close'].iloc[-20:].mean()
    if avg_close == 0:
        return {"status": "Normal", "reason": "Price data is zero, cannot assess risk."}

    # رسک کی حدوں کی وضاحت
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
    """
    رسک کی سطح کی بنیاد پر ATR ضرب کو متحرک طور پر ایڈجسٹ کرتا ہے۔
    """
    if risk_status == "High":
        return 1.5
    if risk_status == "Moderate":
        return 1.8
    return 2.0
