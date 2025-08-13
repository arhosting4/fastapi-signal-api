# filename: level_analyzer.py

import logging
from typing import Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

def find_realistic_tp_sl(df: pd.DataFrame, signal_type: str, symbol_personality: Dict) -> Optional[Tuple[float, float]]:
    """
    ATR اور حالیہ سوئنگ پوائنٹس کی بنیاد پر ایک حقیقت پسندانہ TP/SL کا تعین کرتا ہے۔
    """
    if len(df) < 20:
        return None

    last_close = df['close'].iloc[-1]
    
    # ATR کا حساب لگائیں
    tr = pd.concat([df['high'] - df['low'], abs(df['high'] - df['close'].shift()), abs(df['low'] - df['close'].shift())], axis=1).max(axis=1)
    atr = tr.ewm(span=14, adjust=False).mean().iloc[-1]
    
    if atr == 0:
        return None

    volatility_multiplier = symbol_personality.get("volatility_multiplier", 1.5)
    min_rr_ratio = symbol_personality.get("min_rr_ratio", 1.5)
    
    # SL کا حساب
    if signal_type == 'buy':
        # حالیہ 10 کینڈلز کے نچلے ترین پوائنٹ کو تلاش کریں
        recent_low = df['low'].tail(10).min()
        # SL کو اس نچلے پوائنٹ سے تھوڑا نیچے یا ATR کی بنیاد پر رکھیں
        stop_loss = min(recent_low - atr * 0.25, last_close - atr * volatility_multiplier)
    else: # sell
        # حالیہ 10 کینڈلز کے بلند ترین پوائنٹ کو تلاش کریں
        recent_high = df['high'].tail(10).max()
        stop_loss = max(recent_high + atr * 0.25, last_close + atr * volatility_multiplier)

    # TP کا حساب
    risk = abs(last_close - stop_loss)
    if risk == 0:
        return None
        
    reward = risk * min_rr_ratio
    
    if signal_type == 'buy':
        take_profit = last_close + reward
    else: # sell
        take_profit = last_close - reward
        
    logger.info(f"حقیقت پسندانہ TP/SL ملا: TP={take_profit:.5f}, SL={stop_loss:.5f} (RR: {min_rr_ratio})")
    return take_profit, stop_loss
    
