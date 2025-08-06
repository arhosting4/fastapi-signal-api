# filename: riskguardian.py

import logging
from typing import Dict, Any, List
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# --- مستقل اقدار ---
ATR_PERIOD = 14
VIX_LOW_THRESHOLD = 20  # کم رسک کی حد
VIX_HIGH_THRESHOLD = 45 # زیادہ رسک کی حد

def _calculate_atr_and_vix(df: pd.DataFrame) -> (float, float):
    """
    ATR اور ایک سادہ VIX (Volatility Index) جیسے اسکور کا حساب لگاتا ہے۔
    """
    if len(df) < ATR_PERIOD + 1:
        return 0.0, 50.0 # ڈیفالٹ درمیانہ رسک

    # ATR کا حساب
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean().iloc[-1]
    
    # قیمت کا فیصد کے طور پر ATR
    avg_price = df['close'].iloc[-ATR_PERIOD:].mean()
    if avg_price == 0:
        return 0.0, 50.0
    
    atr_percentage = (atr / avg_price) * 100

    # VIX جیسا اسکور (0-100)
    # یہ اسکور ATR فیصد کو ایک معیاری پیمانے پر لاتا ہے
    # 0.1% ATR کو 20 VIX، 0.5% کو 60 VIX سمجھا جا سکتا ہے
    vix_score = np.clip((atr_percentage * 100), 5, 95)

    return atr_percentage, vix_score

def get_market_analysis(all_pairs_data: Dict[str, List[pd.DataFrame]]) -> Dict[str, Any]:
    """
    تمام بڑے جوڑوں کے ڈیٹا کی بنیاد پر مارکیٹ کے مجموعی رسک کا تجزیہ کرتا ہے۔
    """
    if not all_pairs_data:
        return {
            "risk_level": "Medium",
            "reason": "مارکیٹ ڈیٹا دستیاب نہیں، درمیانے رسک کا اندازہ۔",
            "parameters": {"rr_ratio": 1.5, "confluence_score": 5}
        }

    vix_scores = []
    total_atr_perc = 0
    count = 0

    for symbol, dataframes in all_pairs_data.items():
        if dataframes:
            # تجزیے کے لیے 1 گھنٹے کا ٹائم فریم استعمال کریں
            df_1h = dataframes[0] 
            if not df_1h.empty:
                atr_perc, vix = _calculate_atr_and_vix(df_1h)
                vix_scores.append(vix)
                total_atr_perc += atr_perc
                count += 1

    if not vix_scores:
        return {
            "risk_level": "Medium",
            "reason": "VIX کا حساب لگانے کے لیے ڈیٹا ناکافی، درمیانے رسک کا اندازہ۔",
            "parameters": {"rr_ratio": 1.5, "confluence_score": 5}
        }

    avg_vix = np.mean(vix_scores)
    avg_atr_perc = total_atr_perc / count if count > 0 else 0
    
    reason = f"اوسط اتار چڑھاؤ = {avg_atr_perc:.3f}%, VIX اسکور = {int(avg_vix)}"
    logger.info(f"🛡️ رسک گارڈین تجزیہ: {reason}")

    # رسک کی سطح اور پیرامیٹرز کا تعین کریں
    if avg_vix < VIX_LOW_THRESHOLD:
        return {
            "risk_level": "Low",
            "reason": f"کم رسک ماحول ({reason})",
            "parameters": {"rr_ratio": 1.2, "confluence_score": 4} # نرم شرائط
        }
    elif avg_vix > VIX_HIGH_THRESHOLD:
        return {
            "risk_level": "High",
            "reason": f"زیادہ رسک ماحول ({reason})",
            "parameters": {"rr_ratio": 2.0, "confluence_score": 6} # سخت شرائط
        }
    else:
        return {
            "risk_level": "Medium",
            "reason": f"معمولی رسک ماحول ({reason})",
            "parameters": {"rr_ratio": 1.5, "confluence_score": 5} # معیاری شرائط
    }
        
