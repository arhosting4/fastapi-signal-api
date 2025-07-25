# filename: strategybot.py

import pandas as pd
import pandas_ta as ta
from typing import List, Tuple, Optional, Dict

import config
from schemas import Candle

def calculate_tp_sl(candles: List[Candle], signal_type: str) -> Optional[Tuple[float, float]]:
    """
    ATR اور حالیہ سوئنگ پوائنٹس کی بنیاد پر TP/SL کا حساب لگاتا ہے۔
    یہ ایک زیادہ ذہین طریقہ ہے جو مارکیٹ کی ساخت کو مدنظر رکھتا ہے۔
    """
    if len(candles) < 20:
        return None
    
    df = pd.DataFrame([c.dict() for c in candles])
    
    # اوسط حقیقی حد (Average True Range) کا حساب لگائیں
    atr = ta.atr(df['high'], df['low'], df['close'], length=config.ATR_LENGTH)
    if atr is None or atr.empty or pd.isna(atr.iloc[-1]):
        return None
        
    last_atr = atr.iloc[-1]
    last_close = df['close'].iloc[-1]
    
    # حالیہ 10 کینڈلز میں سب سے اونچی اور سب سے نیچی قیمت تلاش کریں
    recent_high = df['high'].tail(10).max()
    recent_low = df['low'].tail(10).min()
    
    if signal_type == "buy":
        # اسٹاپ لاس حالیہ کم قیمت سے تھوڑا نیچے رکھیں
        sl = recent_low - (last_atr * 0.5)
        # رسک/انعام کا تناسب 1:1.5 سیٹ کریں
        tp = last_close + (last_close - sl) * 1.5
    elif signal_type == "sell":
        # اسٹاپ لاس حالیہ اونچی قیمت سے تھوڑا اوپر رکھیں
        sl = recent_high + (last_atr * 0.5)
        # رسک/انعام کا تناسب 1:1.5 سیٹ کریں
        tp = last_close - (sl - last_close) * 1.5
    else:
        return None

    return tp, sl

def generate_core_signal(candles: List[Candle]) -> Dict[str, str]:
    """
    تیز رفتار اسکیلپنگ کے لیے بہتر بنائی گئی بنیادی سگنل کی منطق۔
    یہ حکمت عملی رجحان کی سمت میں پل بیک (pullback) تلاش کرتی ہے۔
    """
    if len(candles) < config.BBANDS_PERIOD:
        return {"signal": "wait"}

    df = pd.DataFrame([c.dict() for c in candles])
    close = df['close']
    
    # اشارے (Indicators)
    ema_fast = ta.ema(close, length=config.EMA_SHORT_PERIOD)
    ema_slow = ta.ema(close, length=config.EMA_LONG_PERIOD)
    stoch = ta.stoch(df['high'], df['low'], close, k=config.STOCH_K, d=config.STOCH_D)
    
    # یقینی بنائیں کہ تمام اشارے کامیابی سے کیلکولیٹ ہوئے ہیں
    if any(s is None or s.empty for s in [ema_fast, ema_slow, stoch]):
        return {"signal": "wait"}

    # تازہ ترین اقدار حاصل کریں
    last_ema_fast = ema_fast.iloc[-1]
    last_ema_slow = ema_slow.iloc[-1]
    last_stoch_k = stoch.iloc[-1, 0] # Stochastic %K value

    # --- بہتر بنائی گئی اسکیلپنگ منطق ---
    
    # خرید کا سگنل: جب رجحان اوپر کی طرف ہو (تیز EMA سست EMA سے اوپر ہو)
    # اور قیمت عارضی طور پر نیچے آکر اوور سولڈ حالت میں ہو (Stochastic < 35)
    if last_ema_fast > last_ema_slow and last_stoch_k < 35:
        return {"signal": "buy"}
    
    # فروخت کا سگنل: جب رجحان نیچے کی طرف ہو (تیز EMA سست EMA سے نیچے ہو)
    # اور قیمت عارضی طور پر اوپر جا کر اوور باٹ حالت میں ہو (Stochastic > 65)
    if last_ema_fast < last_ema_slow and last_stoch_k > 65:
        return {"signal": "sell"}
        
    # اگر کوئی شرط پوری نہ ہو تو انتظار کریں
    return {"signal": "wait"}
    
