import pandas as pd
import pandas_ta as ta
from typing import List, Tuple, Optional, Dict

# ==============================================================================
# حکمت عملی کے پیرامیٹرز براہ راست یہاں شامل کر دیے گئے ہیں
# ==============================================================================
EMA_SHORT_PERIOD = 10
EMA_LONG_PERIOD = 30
STOCH_K = 14
STOCH_D = 3
BBANDS_PERIOD = 20
ATR_LENGTH = 14
# ==============================================================================

def calculate_tp_sl(candles: List[Dict], signal_type: str) -> Optional[Tuple[float, float]]:
    """
    ATR اور حالیہ سوئنگ پوائنٹس کی بنیاد پر TP/SL کا حساب لگاتا ہے۔
    """
    if len(candles) < 20:
        return None
    
    # --- اہم تبدیلی: اب یہ پہلے سے ہی ڈکشنری ہے ---
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

def generate_core_signal(candles: List[Dict]) -> Dict[str, str]:
    """
    تیز رفتار اسکیلپنگ کے لیے بہتر بنائی گئی بنیادی سگنل کی منطق۔
    """
    if len(candles) < BBANDS_PERIOD:
        return {"signal": "wait"}

    # --- اہم تبدیلی: اب یہ پہلے سے ہی ڈکشنری ہے ---
    df = pd.DataFrame(candles)
    close = df['close']
    
    ema_fast = ta.ema(close, length=EMA_SHORT_PERIOD)
    ema_slow = ta.ema(close, length=EMA_LONG_PERIOD)
    stoch = ta.stoch(df['high'], df['low'], close, k=STOCH_K, d=STOCH_D)
    
    if any(s is None or s.empty for s in [ema_fast, ema_slow, stoch]):
        return {"signal": "wait"}

    last_ema_fast = ema_fast.iloc[-1]
    last_ema_slow = ema_slow.iloc[-1]
    last_stoch_k = stoch.iloc[-1, 0]

    if last_ema_fast > last_ema_slow and last_stoch_k < 35:
        return {"signal": "buy"}
    
    if last_ema_fast < last_ema_slow and last_stoch_k > 65:
        return {"signal": "sell"}
        
    return {"signal": "wait"}
    
