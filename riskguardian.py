# filename: riskguardian.py

import pandas as pd
import numpy as np
from typing import Dict

# 🎯 ATR کا دورانیہ (14 candles کی بنیاد پر)
ATR_LENGTH = 14

def check_risk(current_price: float, sl_price: float) -> Dict[str, str]:
    """
    Stop Loss اور Current Price کی بنیاد پر Risk:Reward چیک کرتا ہے۔
    📌 اگر SL بہت قریب ہو یا R:R کافی نہ ہو تو خطرہ ظاہر کرتا ہے۔
    """
    try:
        # 🔹 Risk:Reward کا تناسب نکالیں
        risk = abs(current_price - sl_price)
        reward = abs(current_price * 1.5 - current_price)
        rr_ratio = reward / risk if risk != 0 else 0

        if rr_ratio < 1.2:
            return {"allowed": False, "reason": f"خطرہ زیادہ ہے (R:R = {rr_ratio:.2f})"}
        else:
            return {"allowed": True, "reason": f"R:R موزوں ہے ({rr_ratio:.2f})"}

    except Exception as e:
        return {"allowed": False, "reason": f"ریسک کیلکولیشن میں خرابی: {str(e)}"}
