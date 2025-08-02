# filename: patternai.py

import pandas as pd
from typing import Dict, Any

def get_pattern_signal(df: pd.DataFrame) -> Dict[str, Any]:
    """
    بنیادی اور معروف کینڈل اسٹک پیٹرنز (Engulfing, Doji, Hammer, Shooting Star) کی شناخت کرتا ہے۔
    Input: candles (old→new), requires at least 3 bars.
    Output: {"signal_type": "bullish"/"bearish"/"neutral", "reason": "..."}
    استعمال: fusion_engine.py (signal strength/QA pipeline), مکمل roadmap compatibility!
    """
    if df is None or len(df) < 3:
        return {"signal_type": "neutral", "reason": "ناکافی ڈیٹا پیٹرن شناخت کے لیے"}

    recent = df.iloc[-3:]
    bullish, bearish, reason = False, False, "کوئی پیٹرن نہ ملا"
    first, second, third = recent.iloc[0], recent.iloc[1], recent.iloc[2]

    # --- Bullish Engulfing Pattern ---
    if (
        first.close < first.open and
        second.close > second.open and
        second.close > first.open and
        (second.close - second.open) > abs(first.open - first.close)
    ):
        bullish = True
        reason = "Bullish Engulfing pattern"

    # --- Bearish Engulfing Pattern ---
    if (
        first.close > first.open and
        second.close < second.open and
        second.open > first.close and
        (second.open - second.close) > abs(first.open - first.close)
    ):
        bearish = True
        reason = "Bearish Engulfing pattern"

    # --- Doji (last two bars: trend indecision/caution) ---
    for c in recent[-2:]:
        body = abs(c.close - c.open)
        rng = c.high - c.low
        if rng > 0 and body / rng < 0.12:
            reason = "Doji: Trend Caution"
            if not bullish and not bearish:
                return {"signal_type": "neutral", "reason": reason}

    # --- Hammer (bullish reversal, recent bar) ---
    if (
        third.close > third.open and
        (third.low < min(second.low, first.low)) and
        (third.open - third.low) > (third.close - third.open) * 1.5
    ):
        bullish = True
        reason = "Hammer pattern"

    # --- Shooting Star (bearish reversal, recent bar) ---
    if (
        third.close < third.open and
        (third.high > max(second.high, first.high)) and
        (third.high - third.close) > (third.open - third.close) * 1.5
    ):
        bearish = True
        reason = "Shooting Star pattern"

    if bullish and not bearish:
        return {"signal_type": "bullish", "reason": reason}
    elif bearish and not bullish:
        return {"signal_type": "bearish", "reason": reason}
    else:
        return {"signal_type": "neutral", "reason": "کوئی خاص reversal یا trend pattern نہ ملا"}
        
