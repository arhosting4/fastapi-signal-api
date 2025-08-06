import logging
from typing import Dict, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

def find_trade_setup_tp_sl(df: pd.DataFrame, signal_type: str, symbol_personality: Dict) -> Optional[Tuple[float, float]]:
    """
    ایک واحد، مضبوط حکمت عملی (رجحان پر پل بیک) کی بنیاد پر TP/SL کا تعین کرتا ہے۔
    """
    if len(df) < 50:
        return None

    # 1. مارکیٹ کے رجحان کی تصدیق کریں
    ema_20 = df['close'].ewm(span=20, adjust=False).mean()
    ema_50 = df['close'].ewm(span=50, adjust=False).mean()
    last_close = df['close'].iloc[-1]

    is_uptrend = last_close > ema_20.iloc[-1] and ema_20.iloc[-1] > ema_50.iloc[-1]
    is_downtrend = last_close < ema_20.iloc[-1] and ema_20.iloc[-1] < ema_50.iloc[-1]

    # اگر سگنل رجحان کے خلاف ہے تو اسے فوراً مسترد کر دیں
    if (signal_type == 'buy' and not is_uptrend) or \
       (signal_type == 'sell' and not is_downtrend):
        logger.info(f"سگنل ({signal_type}) موجودہ رجحان سے مطابقت نہیں رکھتا۔ مسترد۔")
        return None

    # 2. اسٹاپ لاس کا تعین کریں
    atr = (df['high'] - df['low']).ewm(span=14).mean().iloc[-1]
    if atr == 0: return None
    
    sl_multiplier = symbol_personality.get("volatility_multiplier", 1.5)
    stop_loss = None
    
    if signal_type == 'buy':
        # حالیہ 20 کینڈلز کے سوئنگ لو کے نیچے SL رکھیں
        recent_low = df['low'].tail(20).min()
        stop_loss = recent_low - (atr * 0.2)
    else: # sell
        # حالیہ 20 کینڈلز کے سوئنگ ہائی کے اوپر SL رکھیں
        recent_high = df['high'].tail(20).max()
        stop_loss = recent_high + (atr * 0.2)

    # 3. ٹیک پرافٹ کا تعین کریں
    min_rr_ratio = symbol_personality.get("min_rr_ratio", 1.2)
    risk = abs(last_close - stop_loss)
    if risk == 0: return None

    take_profit = last_close + (risk * min_rr_ratio) if signal_type == 'buy' else last_close - (risk * min_rr_ratio)

    logger.info(f"ریپٹر حکمت عملی TP/SL ملا: TP={take_profit:.5f}, SL={stop_loss:.5f} (RR: {min_rr_ratio})")
    return take_profit, stop_loss
    
