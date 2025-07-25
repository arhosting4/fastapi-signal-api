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
    """
    if len(candles) < SUPERTREND_ATR_PERIOD:
        logger.warning("M15 رجحان کے تجزیے کے لیے ناکافی ڈیٹا۔")
        return "Sideways"

    try:
        df = pd.DataFrame(candles)
        heikin_ashi_df = ta.ha(df['open'], df['high'], df['low'], df['close'])
        
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
            
        last_close = heikin_ashi_df.iloc[-1]['HA_close']
        last_supertrend_value = supertrend.iloc[-1][f'SUPERT_{SUPERTREND_ATR_PERIOD}_{SUPERTREND_ATR_MULTIPLIER}.0']

        if last_close > last_supertrend_value:
            return "Uptrend"
        else:
            return "Downtrend"

    except Exception as e:
        logger.error(f"M15 رجحان کے تجزیے میں خرابی: {e}", exc_info=True)
        return "Sideways"

# --- اہم تبدیلی: M5 سگنل کی منطق کو نافذ کرنا ---
def get_m5_signal(candles: List[Dict], m15_trend: str) -> Dict:
    """
    M5 کینڈلز اور M15 رجحان کی بنیاد پر عین انٹری سگنل تلاش کرتا ہے۔
    """
    if len(candles) < SUPERTREND_ATR_PERIOD or len(candles) < RSI_PERIOD:
        return {"signal": "wait", "reason": "M5 تجزیے کے لیے ناکافی ڈیٹا۔"}

    try:
        df = pd.DataFrame(candles)
        heikin_ashi_df = ta.ha(df['open'], df['high'], df['low'], df['close'])
        
        # M5 Heikin-Ashi کینڈلز پر Supertrend کا حساب لگائیں
        supertrend = ta.supertrend(
            high=heikin_ashi_df['HA_high'],
            low=heikin_ashi_df['HA_low'],
            close=heikin_ashi_df['HA_close'],
            length=SUPERTREND_ATR_PERIOD,
            multiplier=SUPERTREND_ATR_MULTIPLIER
        )
        
        # M5 روایتی کینڈلز پر RSI کا حساب لگائیں
        rsi = ta.rsi(df['close'], length=RSI_PERIOD)

        if supertrend is None or rsi is None:
            return {"signal": "wait", "reason": "M5 انڈیکیٹرز کا حساب نہیں لگایا جا سکا۔"}

        # آخری دو کینڈلز کا ڈیٹا حاصل کریں تاکہ کراس اوور کا پتہ چل سکے
        prev_close = heikin_ashi_df.iloc[-2]['HA_close']
        last_close = heikin_ashi_df.iloc[-1]['HA_close']
        prev_supertrend = supertrend.iloc[-2][f'SUPERTd_{SUPERTREND_ATR_PERIOD}_{SUPERTREND_ATR_MULTIPLIER}.0']
        last_supertrend = supertrend.iloc[-1][f'SUPERTd_{SUPERTREND_ATR_PERIOD}_{SUPERTREND_ATR_MULTIPLIER}.0']
        last_rsi = rsi.iloc[-1]

        # خرید کا سگنل: M15 اپ ٹرینڈ میں ہو اور M5 پر Supertrend کراس اوور ہو
        if m15_trend == "Uptrend" and prev_supertrend == -1 and last_supertrend == 1:
            logger.info(f"ممکنہ BUY سگنل ملا۔ M5 RSI: {last_rsi:.2f}")
            return {"signal": "buy", "rsi": last_rsi, "heikin_ashi": heikin_ashi_df.tail(3).to_dict('records')}

        # فروخت کا سگنل: M15 ڈاؤن ٹرینڈ میں ہو اور M5 پر Supertrend کراس اوور ہو
        if m15_trend == "Downtrend" and prev_supertrend == 1 and last_supertrend == -1:
            logger.info(f"ممکنہ SELL سگنل ملا۔ M5 RSI: {last_rsi:.2f}")
            return {"signal": "sell", "rsi": last_rsi, "heikin_ashi": heikin_ashi_df.tail(3).to_dict('records')}

        return {"signal": "wait", "reason": "M5 پر کوئی کراس اوور نہیں ملا۔"}

    except Exception as e:
        logger.error(f"M5 سگنل کے تجزیے میں خرابی: {e}", exc_info=True)
        return {"signal": "wait", "reason": "M5 تجزیے میں خرابی۔"}


def calculate_dynamic_tp_sl(candles: List[Dict], signal_type: str) -> Optional[Tuple[float, float]]:
    """
    M5 ATR کی بنیاد پر متحرک TP/SL کا حساب لگاتا ہے۔
    """
    if len(candles) < ATR_PERIOD_FOR_TP_SL:
        return None
        
    df = pd.DataFrame(candles)
    atr = ta.atr(df['high'], df['low'], df['close'], length=ATR_PERIOD_FOR_TP_SL)
    
    if atr is None or pd.isna(atr.iloc[-1]):
        return None
        
    last_atr = atr.iloc[-1]
    last_close = df['close'].iloc[-1]
    
    # اسکیلپنگ کے لیے رسک ٹو ریوارڈ ریشو (1:1.5)
    if signal_type == "buy":
        sl = last_close - (last_atr * 1.5)
        tp = last_close + (last_atr * 2.25) # 1.5 * 1.5
    elif signal_type == "sell":
        sl = last_close + (last_atr * 1.5)
        tp = last_close - (last_atr * 2.25) # 1.5 * 1.5
    else:
        return None

    return tp, sl
    
