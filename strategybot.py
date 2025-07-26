# filename: strategybot.py

import pandas as pd
import pandas_ta as ta
from typing import List, Tuple, Optional, Dict

# ★★★ خودکار اصلاح: متحرک پیرامیٹرز کے لیے ڈکشنری شامل کی گئی ★★★
STRATEGY_PARAMS = {
    "default": {"ema_short": 10, "ema_long": 30, "stoch_k": 14, "stoch_d": 3, "rsi_period": 14, "rsi_oversold": 35, "rsi_overbought": 65},
    "1m": {"ema_short": 8, "ema_long": 21, "stoch_k": 10, "stoch_d": 3, "rsi_period": 10, "rsi_oversold": 30, "rsi_overbought": 70},
    "5m": {"ema_short": 10, "ema_long": 30, "stoch_k": 14, "stoch_d": 3, "rsi_period": 14, "rsi_oversold": 35, "rsi_overbought": 65},
}
ATR_LENGTH = 14

def calculate_tp_sl(candles: List[Dict], signal_type: str) -> Optional[Tuple[float, float]]:
    """ATR اور حالیہ سوئنگ پوائنٹس کی بنیاد پر TP/SL کا حساب لگاتا ہے۔"""
    if len(candles) < 20: return None
    df = pd.DataFrame(candles)
    atr = ta.atr(df['high'], df['low'], df['close'], length=ATR_LENGTH)
    if atr is None or atr.empty or pd.isna(atr.iloc[-1]): return None
    last_atr, last_close = atr.iloc[-1], df['close'].iloc[-1]
    recent_high, recent_low = df['high'].tail(10).max(), df['low'].tail(10).min()
    if signal_type == "buy":
        sl = recent_low - (last_atr * 0.5)
        tp = last_close + (last_close - sl) * 1.5
    elif signal_type == "sell":
        sl = recent_high + (last_atr * 0.5)
        tp = last_close - (sl - last_close) * 1.5
    else:
        return None
    return tp, sl

def generate_core_signal(candles: List[Dict], timeframe: str) -> Dict[str, str]:
    """
    تیز رفتار اسکیلپنگ کے لیے بہتر بنائی گئی بنیادی سگنل کی منطق۔
    اب یہ ٹائم فریم کی بنیاد پر پیرامیٹرز کو متحرک طور پر ایڈجسٹ کرتا ہے۔
    """
    # ★★★ خودکار اصلاح: ٹائم فریم کی بنیاد پر پیرامیٹرز حاصل کیے گئے ★★★
    params = STRATEGY_PARAMS.get(timeframe, STRATEGY_PARAMS["default"])

    if len(candles) < params["ema_long"]:
        return {"signal": "wait"}

    df = pd.DataFrame(candles)
    close = df['close']
    
    ema_fast = ta.ema(close, length=params["ema_short"])
    ema_slow = ta.ema(close, length=params["ema_long"])
    stoch = ta.stoch(df['high'], df['low'], close, k=params["stoch_k"], d=params["stoch_d"])
    rsi = ta.rsi(close, length=params["rsi_period"])
    
    if any(s is None or s.empty for s in [ema_fast, ema_slow, stoch, rsi]):
        return {"signal": "wait"}

    last_ema_fast = ema_fast.iloc[-1]
    last_ema_slow = ema_slow.iloc[-1]
    last_stoch_k = stoch.iloc[-1, 0]
    last_rsi = rsi.iloc[-1]

    # خریدنے کی شرط: EMA کراس اوور، Stochastic اوورسولڈ، اور RSI بھی اوورسولڈ
    if last_ema_fast > last_ema_slow and last_stoch_k < params["rsi_oversold"] and last_rsi < 45:
        return {"signal": "buy"}
    
    # بیچنے کی شرط: EMA کراس اوور، Stochastic اوورباٹ، اور RSI بھی اوورباٹ
    if last_ema_fast < last_ema_slow and last_stoch_k > params["rsi_overbought"] and last_rsi > 55:
        return {"signal": "sell"}
        
    return {"signal": "wait"}
    
