# filename: riskguardian.py

import logging
from typing import Dict, List
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# --- مستقل اقدار ---
ATR_LENGTH = 14
ADX_LENGTH = 14
VIX_THRESHOLD = 25  # 25 سے اوپر غیر مستحکم، 25 سے نیچے پرامن
ADX_TREND_THRESHOLD = 25 # 25 سے اوپر رجحان، 25 سے نیچے رینج

def _calculate_atr_normalized(df: pd.DataFrame) -> float:
    """فیصد میں نارملائزڈ ATR کا حساب لگاتا ہے۔"""
    if len(df) < ATR_LENGTH + 1:
        return 0.0
        
    df_copy = df.copy()
    high, low, close = df_copy['high'], df_copy['low'], df_copy['close']
    
    df_copy['tr1'] = high - low
    df_copy['tr2'] = abs(high - close.shift(1))
    df_copy['tr3'] = abs(low - close.shift(1))
    
    tr = df_copy[['tr1', 'tr2', 'tr3']].max(axis=1)
    atr = tr.ewm(span=ATR_LENGTH, adjust=False).mean()
    
    last_atr = atr.iloc[-1]
    last_close = close.iloc[-1]
    
    if last_close == 0: return 0.0
    
    normalized_atr = (last_atr / last_close) * 100
    return normalized_atr if pd.notna(normalized_atr) else 0.0

def _calculate_adx(df: pd.DataFrame) -> float:
    """آخری ADX قدر کا حساب لگاتا ہے۔"""
    if len(df) < ADX_LENGTH * 2:
        return 0.0

    df_copy = df.copy()
    high, low, close = df_copy['high'], df_copy['low'], df_copy['close']

    plus_dm = high.diff()
    minus_dm = low.diff().mul(-1)
    plus_dm[(plus_dm < 0) | (plus_dm <= minus_dm)] = 0
    minus_dm[(minus_dm < 0) | (minus_dm <= plus_dm)] = 0

    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    atr = tr.ewm(span=ADX_LENGTH, adjust=False).mean()

    plus_di = (plus_dm.ewm(span=ADX_LENGTH, adjust=False).mean() / atr) * 100
    minus_di = (minus_dm.ewm(span=ADX_LENGTH, adjust=False).mean() / atr) * 100

    dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1)) * 100
    adx = dx.ewm(span=ADX_LENGTH, adjust=False).mean()
    
    return adx.iloc[-1] if not adx.empty and pd.notna(adx.iloc[-1]) else 0.0

def get_market_regime(ohlc_data_map: Dict[str, pd.DataFrame]) -> Dict[str, any]:
    """
    مارکیٹ کے مجموعی نظام کا تعین کرتا ہے (Calm Trend, Volatile Trend, Calm Range, Kill Zone)۔
    یہ VIX (اتار چڑھاؤ) اور ADX (رجحان کی طاقت) دونوں کا استعمال کرتا ہے۔
    """
    if not ohlc_data_map:
        logger.warning("مارکیٹ کے نظام کا تعین کرنے کے لیے کوئی OHLC ڈیٹا نہیں۔ ڈیفالٹ 'Calm Range'۔")
        return {"regime": "Calm Range", "vix_score": 0, "adx_score": 0}

    all_normalized_atrs = []
    all_adx_values = []

    for symbol, df in ohlc_data_map.items():
        if df.empty:
            continue
        
        # VIX اسکور کے لیے اتار چڑھاؤ کا حساب لگائیں
        all_normalized_atrs.append(_calculate_atr_normalized(df))
        
        # ADX اسکور کے لیے رجحان کی طاقت کا حساب لگائیں
        all_adx_values.append(_calculate_adx(df))

    if not all_normalized_atrs or not all_adx_values:
        logger.warning("کسی بھی جوڑے کے لیے ATR/ADX کا حساب نہیں لگایا جا سکا۔ ڈیفالٹ 'Calm Range'۔")
        return {"regime": "Calm Range", "vix_score": 0, "adx_score": 0}

    # اوسط اقدار کی بنیاد پر حتمی اسکور
    avg_volatility_percent = np.mean([v for v in all_normalized_atrs if v > 0])
    avg_adx = np.mean([v for v in all_adx_values if v > 0])
    
    # VIX اسکور: 0-100 کے پیمانے پر اوسط اتار چڑھاؤ
    vix_score = min(100, int(avg_volatility_percent * 200)) # اسکیلنگ فیکٹر
    adx_score = int(avg_adx)

    logger.info(f"مارکیٹ کا تجزیہ: VIX اسکور = {vix_score}, ADX اسکور = {adx_score}")

    # مارکیٹ کے نظام کا تعین
    is_volatile = vix_score > VIX_THRESHOLD
    is_trending = adx_score > ADX_TREND_THRESHOLD

    regime = "Calm Range" # ڈیفالٹ
    if is_trending and not is_volatile:
        regime = "Calm Trend"
    elif is_trending and is_volatile:
        regime = "Volatile Trend"
    elif not is_trending and is_volatile:
        regime = "Kill Zone"
    # اگر is_trending=False اور is_volatile=False ہے، تو یہ 'Calm Range' ہی رہے گا۔

    logger.info(f"♟️ ماسٹر مائنڈ فیصلہ: مارکیٹ کا نظام = {regime}")
    
    return {"regime": regime, "vix_score": vix_score, "adx_score": adx_score}
    
