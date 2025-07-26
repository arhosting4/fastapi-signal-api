# filename: strategybot.py

import pandas as pd
import pandas_ta as ta
from typing import List, Tuple, Optional, Dict

# --- خودکار اصلاح: متحرک ٹائم فریم سیٹنگز ---
# ہر ٹائم فریم کے لیے بہترین انڈیکیٹر سیٹنگز
TIMEFRAME_SETTINGS = {
    "1m":  {"EMA_SHORT": 5,  "EMA_LONG": 15, "STOCH_K": 14, "STOCH_D": 3, "RSI_PERIOD": 14, "RSI_OVERSOLD": 35, "RSI_OVERBOUGHT": 65},
    "3m":  {"EMA_SHORT": 8,  "EMA_LONG": 21, "STOCH_K": 14, "STOCH_D": 3, "RSI_PERIOD": 14, "RSI_OVERSOLD": 30, "RSI_OVERBOUGHT": 70},
    "5m":  {"EMA_SHORT": 8,  "EMA_LONG": 21, "STOCH_K": 14, "STOCH_D": 3, "RSI_PERIOD": 14, "RSI_OVERSOLD": 30, "RSI_OVERBOUGHT": 70},
    "15m": {"EMA_SHORT": 10, "EMA_LONG": 30, "STOCH_K": 14, "STOCH_D": 3, "RSI_PERIOD": 14, "RSI_OVERSOLD": 30, "RSI_OVERBOUGHT": 70},
}

def calculate_tp_sl(candles: List[Dict], signal_type: str, timeframe: str) -> Optional[Tuple[float, float]]:
    """
    ATR اور حالیہ سوئنگ پوائنٹس کی بنیاد پر TP/SL کا حساب لگاتا ہے۔
    """
    if len(candles) < 20:
        return None
    
    df = pd.DataFrame(candles)
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])

    atr = ta.atr(df['high'], df['low'], df['close'], length=14)
    if atr is None or atr.empty or pd.isna(atr.iloc[-1]):
        return None
        
    last_atr = atr.iloc[-1]
    last_close = df['close'].iloc[-1]
    
    recent_high = df['high'].tail(10).max()
    recent_low = df['low'].tail(10).min()
    
    # رسک ٹو ریوارڈ ریشو
    risk_reward_ratio = 1.5
    
    if signal_type == "buy":
        sl = recent_low - (last_atr * 0.5)
        tp = last_close + (last_close - sl) * risk_reward_ratio
    elif signal_type == "sell":
        sl = recent_high + (last_atr * 0.5)
        tp = last_close - (sl - last_close) * risk_reward_ratio
    else:
        return None

    return tp, sl

def generate_core_signal(candles: List[Dict], timeframe: str) -> Dict[str, str]:
    """
    RSI کی تصدیق کے ساتھ بہتر بنائی گئی بنیادی سگنل کی منطق۔
    یہ اب ٹائم فریم کی بنیاد پر متحرک سیٹنگز استعمال کرتا ہے۔
    """
    # ٹائم فریم کے لیے سیٹنگز حاصل کریں، اگر نہ ملیں تو 15m کی ڈیفالٹ استعمال کریں
    settings = TIMEFRAME_SETTINGS.get(timeframe, TIMEFRAME_SETTINGS["15m"])

    if len(candles) < settings["EMA_LONG"]:
        return {"signal": "wait"}

    df = pd.DataFrame(candles)
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])
    close = df['close']
    
    # انڈیکیٹرز کا حساب لگائیں
    ema_fast = ta.ema(close, length=settings["EMA_SHORT"])
    ema_slow = ta.ema(close, length=settings["EMA_LONG"])
    stoch = ta.stoch(df['high'], df['low'], close, k=settings["STOCH_K"], d=settings["STOCH_D"])
    rsi = ta.rsi(close, length=settings["RSI_PERIOD"])
    
    if any(s is None or s.empty for s in [ema_fast, ema_slow, stoch, rsi]):
        return {"signal": "wait"}

    # آخری قدریں حاصل کریں
    last_ema_fast = ema_fast.iloc[-1]
    last_ema_slow = ema_slow.iloc[-1]
    last_stoch_k = stoch.iloc[-1, 0]
    last_rsi = rsi.iloc[-1]

    # خرید کی شرائط (Buy Conditions)
    is_buy_trend = last_ema_fast > last_ema_slow
    is_stoch_oversold = last_stoch_k < settings["RSI_OVERSOLD"] # Stochastic کے لیے بھی RSI کی حد استعمال کر رہے ہیں
    is_rsi_not_overbought = last_rsi < 80 # یقینی بنائیں کہ مارکیٹ بہت زیادہ خریدی ہوئی نہ ہو

    if is_buy_trend and is_stoch_oversold and is_rsi_not_overbought:
        return {"signal": "buy"}
    
    # فروخت کی شرائط (Sell Conditions)
    is_sell_trend = last_ema_fast < last_ema_slow
    is_stoch_overbought = last_stoch_k > settings["RSI_OVERBOUGHT"]
    is_rsi_not_oversold = last_rsi > 20 # یقینی بنائیں کہ مارکیٹ بہت زیادہ بیچی ہوئی نہ ہو

    if is_sell_trend and is_stoch_overbought and is_rsi_not_oversold:
        return {"signal": "sell"}
        
    return {"signal": "wait"}
    
