import logging
from typing import Dict, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

def find_fortress_tp_sl(df: pd.DataFrame, signal_type: str, symbol_personality: Dict) -> Optional[Tuple[float, float]]:
    """
    ایک ناقابلِ تسخیر اور تکنیکی طور پر درست TP/SL کا تعین کرتا ہے جو حقیقی مارکیٹ کی ساخت پر مبنی ہو۔
    یہ ورژن سادگی اور طاقت پر مرکوز ہے۔
    """
    if len(df) < 34:
        logger.warning("ناکافی ڈیٹا، TP/SL کا حساب نہیں لگایا جا سکتا۔")
        return None

    last_close = df['close'].iloc[-1]
    
    # 1. اسٹاپ لاس کا تعین: مارکیٹ کی اصل ساخت کی بنیاد پر
    stop_loss = None
    
    # حالیہ 34 کینڈلز کا جائزہ لیں، جو کہ مارکیٹ کی تازہ ترین اہم ساخت کو ظاہر کرتا ہے
    recent_df = df.tail(34)

    if signal_type == 'buy':
        # اسٹاپ لاس کو حالیہ رینج کے سب سے نچلے پوائنٹ (Significant Swing Low) کے نیچے رکھیں
        structure_low = recent_df['low'].min()
        stop_loss = structure_low
    else: # signal_type == 'sell'
        # اسٹاپ لاس کو حالیہ رینج کے سب سے اونچے پوائنٹ (Significant Swing High) کے اوپر رکھیں
        structure_high = recent_df['high'].max()
        stop_loss = structure_high

    # 2. رسک کا حساب لگائیں
    risk = abs(last_close - stop_loss)

    # اگر رسک صفر ہے یا بہت زیادہ ہے تو ٹریڈ کو مسترد کر دیں
    if risk == 0:
        logger.warning("رسک کا حساب نہیں لگایا جا سکا (رسک صفر ہے)۔")
        return None
    
    # ایک حفاظتی فلٹر: اگر SL انٹری کے بہت قریب ہے تو ٹریڈ نہ کریں
    # یہ اسپریڈ اور معمولی اتار چڑھاؤ سے بچائے گا
    atr = (df['high'] - df['low']).ewm(span=14).mean().iloc[-1]
    if risk < atr:
        logger.warning(f"اسٹاپ لاس ({risk:.5f}) ATR ({atr:.5f}) سے بھی کم ہے، بہت خطرناک۔ سگنل مسترد۔")
        return None

    # 3. ٹیک پرافٹ کا تعین کریں
    min_rr_ratio = symbol_personality.get("min_rr_ratio", 1.5)
    take_profit = last_close + (risk * min_rr_ratio) if signal_type == 'buy' else last_close - (risk * min_rr_ratio)

    logger.info(f"فورٹریس TP/SL ملا: TP={take_profit:.5f}, SL={stop_loss:.5f} (RR: {min_rr_ratio})")
    return take_profit, stop_loss
    
