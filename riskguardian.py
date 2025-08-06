import logging
from typing import Dict, List
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

ATR_LENGTH = 14

def _calculate_atr(df: pd.DataFrame, period: int) -> float:
    """ایک ڈیٹا فریم کے لیے آخری ATR قدر کا حساب لگاتا ہے۔"""
    if len(df) < period + 1:
        return 0.0
        
    df_copy = df.copy()
    high, low, close = df_copy['high'], df_copy['low'], df_copy['close']
    
    df_copy['h-l'] = high - low
    df_copy['h-pc'] = abs(high - close.shift(1))
    df_copy['l-pc'] = abs(low - close.shift(1))
    
    tr = df_copy[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()
    
    return atr.iloc[-1] if not atr.empty and pd.notna(atr.iloc[-1]) else 0.0

def get_market_regime(ohlc_data_map: Dict[str, pd.DataFrame]) -> Dict[str, any]:
    """
    تمام بڑے جوڑوں کے اتار چڑھاؤ کا تجزیہ کرکے مارکیٹ کے مجموعی "موڈ" کا تعین کرتا ہے۔
    یہ اب حکمت عملی کا نام واپس نہیں کرتا، بلکہ صرف مارکیٹ کی حالت بتاتا ہے۔
    """
    if not ohlc_data_map:
        logger.warning("مارکیٹ کے نظام کا تعین کرنے کے لیے کوئی OHLC ڈیٹا نہیں۔ ڈیفالٹ 'Calm' موڈ۔")
        return {"regime": "Calm", "vix_score": 25}

    normalized_atrs = []
    for symbol, df in ohlc_data_map.items():
        if df.empty or len(df) < ATR_LENGTH + 1:
            continue
            
        avg_price = df['close'].iloc[-20:].mean()
        if avg_price == 0:
            continue
            
        atr = _calculate_atr(df, ATR_LENGTH)
        normalized_atr = (atr / avg_price) * 100  # فیصد کے طور پر ATR
        normalized_atrs.append(normalized_atr)

    if not normalized_atrs:
        logger.warning("کسی بھی جوڑے کے لیے ATR کا حساب نہیں لگایا جا سکا۔ ڈیفالٹ 'Calm' موڈ۔")
        return {"regime": "Calm", "vix_score": 25}

    # VIX اسکور: 0-100 کے پیمانے پر اوسط اتار چڑھاؤ
    avg_volatility_percent = np.mean(normalized_atrs)
    vix_score = min(100, int(avg_volatility_percent * 200)) # اسکیلنگ فیکٹر

    logger.info(f"مارکیٹ کا تجزیہ: اوسط اتار چڑھاؤ = {avg_volatility_percent:.3f}%, VIX اسکور = {vix_score}")

    if vix_score > 75:
        return {"regime": "Stormy", "vix_score": vix_score}
    elif vix_score > 40:
        return {"regime": "Volatile", "vix_score": vix_score}
    else:
        return {"regime": "Calm", "vix_score": vix_score}
        
