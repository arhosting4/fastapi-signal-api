# filename: strategybot.py

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional, Dict, Any

# ==============================================================================
# حکمت عملی کے پیرامیٹرز
# ==============================================================================
EMA_SHORT_PERIOD = 10
EMA_LONG_PERIOD = 30
STOCH_K = 14
STOCH_D = 3
RSI_PERIOD = 14
BBANDS_PERIOD = 20
ATR_LENGTH = 14
# ==============================================================================

# ★★★ خود مختار اور محفوظ انڈیکیٹر فنکشنز ★★★

def calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    """صفر سے تقسیم کے مسئلے سے محفوظ RSI کا حساب لگاتا ہے۔"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, 1e-9) 
    return 100 - (100 / (1 + rs))

def calculate_bbands(data: pd.Series, period: int) -> pd.DataFrame:
    """بولنگر بینڈز کا حساب لگاتا ہے۔"""
    sma = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    upper_band = sma + (std * 2)
    lower_band = sma - (std * 2)
    return pd.DataFrame({'BBl': lower_band, 'BBu': upper_band})

def calculate_stoch(high: pd.Series, low: pd.Series, close: pd.Series, k: int, d: int) -> pd.DataFrame:
    """صفر سے تقسیم کے مسئلے سے محفوظ Stochastic Oscillator کا حساب لگاتا ہے۔"""
    low_k = low.rolling(window=k).min()
    high_k = high.rolling(window=k).max()
    stoch_k = 100 * (close - low_k) / (high_k - low_k).replace(0, 1e-9)
    stoch_d = stoch_k.rolling(window=d).mean()
    return pd.DataFrame({'STOCHk': stoch_k, 'STOCHd': stoch_d})

def calculate_tp_sl(candles: List[Dict], signal_type: str) -> Optional[Tuple[float, float]]:
    """ATR کی بنیاد پر TP/SL کا حساب لگاتا ہے۔"""
    if len(candles) < 20: return None
    df = pd.DataFrame(candles)
    df['h-l'] = df['high'] - df['low']
    df['h-pc'] = np.abs(df['high'] - df['close'].shift())
    df['l-pc'] = np.abs(df['low'] - df['close'].shift())
    tr = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    atr = tr.rolling(window=ATR_LENGTH).mean()
    if atr.empty or pd.isna(atr.iloc[-1]): return None
    last_atr = atr.iloc[-1]
    last_close = df['close'].iloc[-1]
    recent_high = df['high'].tail(10).max()
    recent_low = df['low'].tail(10).min()
    if signal_type == "buy":
        sl = recent_low - (last_atr * 0.5)
        tp = last_close + (last_close - sl) * 1.5
    elif signal_type == "sell":
        sl = recent_high + (last_atr * 0.5)
        tp = last_close - (sl - last_close) * 1.5
    else: return None
    return tp, sl

def generate_core_signal(candles: List[Dict]) -> Dict[str, Any]:
    """تمام انڈیکیٹرز پر مبنی بنیادی سگنل کی منطق۔"""
    if len(candles) < max(EMA_LONG_PERIOD, BBANDS_PERIOD, RSI_PERIOD):
        return {"signal": "wait", "indicators": {}}
    df = pd.DataFrame(candles)
    close = df['close']
    ema_fast = close.ewm(span=EMA_SHORT_PERIOD, adjust=False).mean()
    ema_slow = close.ewm(span=EMA_LONG_PERIOD, adjust=False).mean()
    stoch = calculate_stoch(df['high'], df['low'], close, STOCH_K, STOCH_D)
    rsi = calculate_rsi(close, RSI_PERIOD)
    bbands = calculate_bbands(close, BBANDS_PERIOD)
    if any(s.empty for s in [ema_fast, ema_slow, stoch, rsi, bbands]):
        return {"signal": "wait", "indicators": {}}
    last_close = close.iloc[-1]
    last_ema_fast = ema_fast.iloc[-1]
    last_ema_slow = ema_slow.iloc[-1]
    last_stoch_k = stoch['STOCHk'].iloc[-1]
    last_rsi = rsi.iloc[-1]
    last_bb_lower = bbands['BBl'].iloc[-1]
    last_bb_upper = bbands['BBu'].iloc[-1]
    if any(pd.isna(v) for v in [last_ema_fast, last_ema_slow, last_stoch_k, last_rsi, last_bb_lower, last_bb_upper]):
        return {"signal": "wait", "indicators": {}}
    indicators_data = {"ema_cross": "bullish" if last_ema_fast > last_ema_slow else "bearish", "stoch_k": round(last_stoch_k, 2), "rsi": round(last_rsi, 2), "price_vs_bb": "near_lower" if last_close <= last_bb_lower else ("near_upper" if last_close >= last_bb_upper else "middle")}
    buy_conditions = [last_ema_fast > last_ema_slow, last_stoch_k < 40, last_rsi > 50, last_close > last_bb_lower]
    sell_conditions = [last_ema_fast < last_ema_slow, last_stoch_k > 60, last_rsi < 50, last_close < last_bb_upper]
    if all(buy_conditions): return {"signal": "buy", "indicators": indicators_data}
    if all(sell_conditions): return {"signal": "sell", "indicators": indicators_data}
    return {"signal": "wait", "indicators": {}}
