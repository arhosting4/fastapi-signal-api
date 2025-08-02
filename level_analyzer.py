# filename: level_analyzer.py

import pandas as pd

def find_optimal_tp_sl(df: pd.DataFrame, signal_type: str):
    """
    Support/resistance یا recent high/low پر TP/SL auto-set کرے گا!
    Inputs:
        - df: Pandas DataFrame, sorted oldest→latest, must include columns 'high', 'low', 'close'
        - signal_type: "buy" یا "sell"
    Returns: (tp (float), sl (float)) — دونوں اچھی طرح rounded (4 decimals)
    """
    if df is None or len(df) < 34:
        raise ValueError("ناکافی ڈیٹا — کم از کم 34 candles required.")

    close = df["close"]
    last_price = close.iloc[-1]

    if signal_type == "buy":
        sl = min(df["low"].iloc[-12:])
        tp = max(df["high"].iloc[-8:])
        if tp <= last_price:
            tp = last_price + (last_price - sl)
    elif signal_type == "sell":
        sl = max(df["high"].iloc[-12:])
        tp = min(df["low"].iloc[-8:])
        if tp >= last_price:
            tp = last_price - (sl - last_price)
    else:
        raise ValueError("signal_type must be 'buy' or 'sell'.")

    return round(tp, 4), round(sl, 4)
    
