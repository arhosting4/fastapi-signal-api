# filename: level_analyzer.py

import logging
from typing import Optional, Tuple, Dict
import pandas as pd

logger = logging.getLogger(__name__)

def find_realistic_tp_sl(
    df: pd.DataFrame, 
    signal_type: str, 
    symbol_personality: Dict, 
    strategy_type: str
) -> Optional[Tuple[float, float]]:
    """
    ATR، سوئنگ پوائنٹس، اور حکمت عملی کی قسم کی بنیاد پر ایک متحرک اور حقیقت پسندانہ TP/SL کا تعین کرتا ہے۔
    """
    if len(df) < 20:
        logger.warning("TP/SL کا حساب لگانے کے لیے ناکافی ڈیٹا۔")
        return None

    last_close = df['close'].iloc[-1]
    
    # ATR کا حساب لگائیں تاکہ مارکیٹ کے موجودہ اتار چڑھاؤ کو سمجھا جا سکے
    tr = pd.concat([
        df['high'] - df['low'], 
        abs(df['high'] - df['close'].shift()), 
        abs(df['low'] - df['close'].shift())
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=14, adjust=False).mean().iloc[-1]
    
    if atr == 0:
        logger.warning("ATR صفر ہے، TP/SL کا حساب نہیں لگایا جا سکتا۔")
        return None

    # --- متحرک رسک/ریوارڈ کا تناسب ---
    # حکمت عملی کی قسم کی بنیاد پر رسک/ریوارڈ کا تناسب منتخب کریں
    if strategy_type == "trending":
        # ٹرینڈنگ مارکیٹ میں بڑا ریوارڈ حاصل کرنے کی کوشش کریں
        default_rr = 1.5
    elif strategy_type == "ranging":
        # رینجنگ مارکیٹ میں چھوٹا، فوری منافع حاصل کریں
        default_rr = 1.0
    else: # ڈیفالٹ یا بریک آؤٹ کے لیے
        default_rr = 1.2

    # اثاثہ کی شخصیت سے پیرامیٹرز حاصل کریں
    volatility_multiplier = symbol_personality.get("volatility_multiplier", 1.5)
    min_rr_ratio = symbol_personality.get("min_rr_ratio", default_rr)
    
    # اسٹاپ لاس کا حساب لگائیں
    if signal_type == 'buy':
        # اسٹاپ لاس حالیہ کم ترین سطح سے تھوڑا نیچے یا ATR پر مبنی فاصلے پر ہوگا
        recent_low = df['low'].tail(10).min()
        stop_loss = min(recent_low - atr * 0.25, last_close - atr * volatility_multiplier)
    else: # 'sell'
        # اسٹاپ لاس حالیہ بلند ترین سطح سے تھوڑا اوپر یا ATR پر مبنی فاصلے پر ہوگا
        recent_high = df['high'].tail(10).max()
        stop_loss = max(recent_high + atr * 0.25, last_close + atr * volatility_multiplier)

    # رسک اور ریوارڈ کا حساب لگائیں
    risk = abs(last_close - stop_loss)
    if risk == 0:
        logger.warning("رسک صفر ہے، TP/SL کا حساب نہیں لگایا جا سکتا۔")
        return None
        
    reward = risk * min_rr_ratio
    
    # ٹیک پرافٹ کا حساب لگائیں
    if signal_type == 'buy':
        take_profit = last_close + reward
    else: # 'sell'
        take_profit = last_close - reward
        
    logger.info(f"حقیقت پسندانہ TP/SL ملا ({strategy_type}): TP={take_profit:.5f}, SL={stop_loss:.5f} (RR: {min_rr_ratio})")
    return take_profit, stop_loss
        
