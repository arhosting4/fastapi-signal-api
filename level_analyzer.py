import logging
from typing import Dict, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

def find_realistic_tp_sl(df: pd.DataFrame, signal_type: str, symbol_personality: Dict) -> Optional[Tuple[float, float]]:
    """
    ایک سادہ، موثر اور حقیقت پسندانہ حکمت عملی کی بنیاد پر TP/SL کا تعین کرتا ہے۔
    """
    if len(df) < 34:
        return None

    last_close = df['close'].iloc[-1]
    
    # 1. ATR کا حساب لگائیں (مارکیٹ کے اتار چڑھاؤ کو سمجھنے کے لیے)
    atr = (df['high'] - df['low']).ewm(span=14).mean().iloc[-1]
    if atr == 0: return None

    # 2. اسٹاپ لاس کا تعین کریں (ایک محفوظ اور منطقی جگہ پر)
    sl_multiplier = symbol_personality.get("volatility_multiplier", 1.5)
    risk_points = atr * sl_multiplier
    
    stop_loss = last_close - risk_points if signal_type == 'buy' else last_close + risk_points

    # 3. ٹیک پرافٹ کا تعین کریں (ایک قابلِ قدر منافع کے لیے)
    min_rr_ratio = symbol_personality.get("min_rr_ratio", 1.5)
    reward_points = risk_points * min_rr_ratio
    
    take_profit = last_close + reward_points if signal_type == 'buy' else last_close - reward_points

    logger.info(f"حقیقت پسندانہ TP/SL ملا: TP={take_profit:.5f}, SL={stop_loss:.5f} (RR: {min_rr_ratio})")
    return take_profit, stop_loss
    
