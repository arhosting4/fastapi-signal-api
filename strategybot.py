# filename: strategybot.py

import pandas as pd
import pandas_ta as ta
from typing import List, Tuple, Optional, Dict

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

def calculate_tp_sl(candles: List[Dict], signal_type: str) -> Optional[Tuple[float, float]]:
    """
    ATR اور حالیہ سوئنگ پوائنٹس کی بنیاد پر TP/SL کا حساب لگاتا ہے۔
    """
    if len(candles) < 20:
        return None
    
    df = pd.DataFrame(candles)
    
    atr = ta.atr(df['high'], df['low'], df['close'], length=ATR_LENGTH)
    if atr is None or atr.empty or pd.isna(atr.iloc[-1]):
        return None
        
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
    else:
        return None

    return tp, sl

def generate_core_signal(candles: List[Dict]) -> Dict[str, Any]:
    """
    متعدد اشاروں (EMA, Stoch, RSI, BBands) پر مبنی بنیادی سگنل کی منطق۔
    """
    if len(candles) < max(EMA_LONG_PERIOD, BBANDS_PERIOD, RSI_PERIOD):
        return {"signal": "wait", "indicators": {}}

    df = pd.DataFrame(candles)
    close = df['close']
    
    # تمام انڈیکیٹرز کا حساب لگائیں
    ema_fast = ta.ema(close, length=EMA_SHORT_PERIOD)
    ema_slow = ta.ema(close, length=EMA_LONG_PERIOD)
    stoch = ta.stoch(df['high'], df['low'], close, k=STOCH_K, d=STOCH_D)
    rsi = ta.rsi(close, length=RSI_PERIOD)
    bbands = ta.bbands(close, length=BBANDS_PERIOD)
    
    if any(s is None or s.empty for s in [ema_fast, ema_slow, stoch, rsi, bbands]):
        return {"signal": "wait", "indicators": {}}

    # آخری قدریں حاصل کریں
    last_close = close.iloc[-1]
    last_ema_fast = ema_fast.iloc[-1]
    last_ema_slow = ema_slow.iloc[-1]
    last_stoch_k = stoch.iloc[-1, 0]
    last_rsi = rsi.iloc[-1]
    last_bb_lower = bbands.iloc[-1, 0] # BBl_20_2.0
    last_bb_upper = bbands.iloc[-1, 2] # BBu_20_2.0

    # انڈیکیٹرز کی حالت کو محفوظ کریں تاکہ وجہ بنانے میں استعمال ہو سکے
    indicators_data = {
        "ema_cross": "bullish" if last_ema_fast > last_ema_slow else "bearish",
        "stoch_k": round(last_stoch_k, 2),
        "rsi": round(last_rsi, 2),
        "price_vs_bb": "near_lower" if last_close <= last_bb_lower else ("near_upper" if last_close >= last_bb_upper else "middle")
    }

    # خریدنے کی شرائط
    buy_conditions = [
        last_ema_fast > last_ema_slow,  # تیزی کا رجحان
        last_stoch_k < 40,              # اوور سولڈ نہیں، لیکن نیچے ہے
        last_rsi > 50,                  # تیزی کا مومینٹم
        last_close > last_bb_lower      # قیمت نچلے بینڈ سے نیچے نہیں گری
    ]

    # بیچنے کی شرائط
    sell_conditions = [
        last_ema_fast < last_ema_slow,  # مندی کا رجحان
        last_stoch_k > 60,              # اوور باٹ نہیں، لیکن اوپر ہے
        last_rsi < 50,                  # مندی کا مومینٹم
        last_close < last_bb_upper      # قیمت اوپری بینڈ سے اوپر نہیں گئی
    ]

    if all(buy_conditions):
        return {"signal": "buy", "indicators": indicators_data}
    
    if all(sell_conditions):
        return {"signal": "sell", "indicators": indicators_data}
        
    return {"signal": "wait", "indicators": {}}
    
