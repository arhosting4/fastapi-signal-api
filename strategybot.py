# filename: strategybot.py

# ... (تمام امپورٹس اور پچھلے فنکشنز ویسے ہی رہیں گے) ...
import json
import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from level_analyzer import find_optimal_tp_sl
from config import tech_settings

logger = logging.getLogger(__name__)
WEIGHTS_FILE = "strategy_weights.json"

# ... (calculate_rsi, calculate_stoch, وغیرہ جیسے تمام فنکشنز یہاں آئیں گے) ...
# (اوپر سے کوڈ کاپی کریں، صرف آخری فنکشن تبدیل ہو گا)

def calculate_tp_sl(df: pd.DataFrame, signal_type: str) -> Optional[Tuple[float, float]]:
    """
    بہترین TP/SL لیولز کا حساب لگاتا ہے اور ان کی منطقی حیثیت کو یقینی بناتا ہے۔
    """
    if df.empty or len(df) < 34:
        logger.warning("TP/SL کے حساب کے لیے ناکافی ڈیٹا۔")
        return None
    try:
        result = find_optimal_tp_sl(df, signal_type)
        
        # اصلاح: حتمی حفاظتی جانچ
        if result is None:
            return None

        tp, sl = result
        last_close = df['close'].iloc[-1]

        # یقینی بنائیں کہ TP/SL منطقی ہیں
        if signal_type == 'buy' and (tp <= last_close or sl >= last_close):
            logger.error(f"غیر منطقی TP/SL کا حساب لگایا گیا (Buy): TP={tp}, SL={sl}, Close={last_close}")
            return None
        if signal_type == 'sell' and (tp >= last_close or sl <= last_close):
            logger.error(f"غیر منطقی TP/SL کا حساب لگایا گیا (Sell): TP={tp}, SL={sl}, Close={last_close}")
            return None
            
        return result

    except Exception as e:
        logging.error(f"TP/SL کیلکولیشن میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        return None

# ... (بقیہ فائل کا کوڈ ویسے ہی رہے گا) ...
