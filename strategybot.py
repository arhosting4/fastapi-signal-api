# filename: strategybot.py

import pandas as pd
import pandas_ta as ta
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# ==============================================================================
# نئی اسکیلپنگ حکمت عملی کے پیرامیٹرز
# ==============================================================================
SUPERTREND_ATR_PERIOD = 10
SUPERTREND_ATR_MULTIPLIER = 3.0
RSI_PERIOD = 14
ATR_PERIOD_FOR_TP_SL = 14

def get_m15_trend(candles: List[Dict]) -> str:
    """
    M15 کینڈلز کی بنیاد پر بڑے رجحان کی شناخت کرتا ہے۔
    یہ فنکشن Heikin-Ashi کینڈلز پر Supertrend کا استعمال کرتا ہے۔
    """
    if len(candles) < SUPERTREND_ATR_PERIOD:
        logger.warning("M15 رجحان کے تجزیے کے لیے ناکافی ڈیٹا۔")
        return "Sideways"

    try:
        df = pd.DataFrame(candles)
        
        # 1. Heikin-Ashi کینڈلز بنائیں
        heikin_ashi_df = ta.ha(df['open'], df['high'], df['low'], df['close'])
        
        # 2. Heikin-Ashi کینڈلز پر Supertrend کا حساب لگائیں
        supertrend = ta.supertrend(
            high=heikin_ashi_df['HA_high'],
            low=heikin_ashi_df['HA_low'],
            close=heikin_ashi_df['HA_close'],
            length=SUPERTREND_ATR_PERIOD,
            multiplier=SUPERTREND_ATR_MULTIPLIER
        )

        if supertrend is None or supertrend.empty:
            logger.warning("M15 Supertrend کا حساب نہیں لگایا جا سکا۔")
            return "Sideways"
            
        # آخری کینڈل کی بنیاد پر رجحان کا تعین کریں
        last_close = heikin_ashi_df.iloc[-1]['HA_close']
        last_supertrend = supertrend.iloc[-1][f'SUPERT_{SUPERTREND_ATR_PERIOD}_{SUPERTREND_ATR_MULTIPLIER}.0']

        if last_close > last_supertrend:
            logger.info("M15 رجحان کی شناخت: Uptrend")
            return "Uptrend"
        else:
            logger.info("M15 رجحان کی شناخت: Downtrend")
            return "Downtrend"

    except Exception as e:
        logger.error(f"M15 رجحان کے تجزیے میں خرابی: {e}", exc_info=True)
        return "Sideways"

def get_m5_signal(candles: List[Dict], m15_trend: str) -> Dict:
    """
    M5 کینڈلز اور M15 رجحان کی بنیاد پر عین انٹری سگنل تلاش کرتا ہے۔
    (نوٹ: یہ فنکشن ابھی صرف ایک پلیس ہولڈر ہے۔ ہم اسے اگلے مرحلے میں مکمل کریں گے۔)
    """
    logger.info(f"M5 سگنل کی تلاش شروع کی جا رہی ہے، M15 رجحان: {m15_trend}")
    # TODO: اگلے مرحلے میں M5 Supertrend اور RSI کی منطق یہاں شامل کی جائے گی۔
    return {"signal": "wait", "reason": "M5 تجزیہ ابھی نافذ نہیں ہوا۔"}


def calculate_dynamic_tp_sl(candles: List[Dict], signal_type: str) -> Optional[Tuple[float, float]]:
    """
    M5 ATR کی بنیاد پر متحرک TP/SL کا حساب لگاتا ہے۔
    (نوٹ: یہ فنکشن بھی اگلے مراحل میں استعمال ہوگا۔)
    """
    if len(candles) < ATR_PERIOD_FOR_TP_SL:
        return None
        
    df = pd.DataFrame(candles)
    atr = ta.atr(df['high'], df['low'], df['close'], length=ATR_PERIOD_FOR_TP_SL)
    
    if atr is None or pd.isna(atr.iloc[-1]):
        return None
        
    last_atr = atr.iloc[-1]
    last_close = df['close'].iloc[-1]
    
    if signal_type == "buy":
        sl = last_close - (last_atr * 1.5)
        tp = last_close + (last_atr * 2.0)
    elif signal_type == "sell":
        sl = last_close + (last_atr * 1.5)
        tp = last_close - (last_atr * 2.0)
    else:
        return None

    return tp, sl

