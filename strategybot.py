# filename: strategybot.py

import pandas as pd
import pandas_ta as ta
from typing import List, Dict, Any, Optional, Tuple

def generate_core_signal(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    5 تکنیکی اشاروں کی بنیاد پر ایک بنیادی سگنل پیدا کرتا ہے۔
    """
    if len(candles) < 34: # MACD کے لیے کم از کم 34 پیریڈز کی ضرورت ہوتی ہے
        return {"signal": "wait", "reason": "Not enough data for MACD."}

    df = pd.DataFrame(candles)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)

    # تکنیکی اشارے کیلکولیٹ کریں
    df.ta.sma(length=20, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.macd(fast=12, slow=26, signal=9, append=True)
    df.ta.bbands(length=20, std=2, append=True)
    df.ta.stoch(k=14, d=3, smooth_k=3, append=True)

    # آخری کینڈل کا ڈیٹا حاصل کریں
    last = df.iloc[-1]
    
    buy_signals = 0
    sell_signals = 0

    # 1. SMA Signal
    if last['close'] > last['SMA_20']: buy_signals += 1
    elif last['close'] < last['SMA_20']: sell_signals += 1

    # 2. RSI Signal
    if last['RSI_14'] < 30: buy_signals += 1
    elif last['RSI_14'] > 70: sell_signals += 1

    # 3. MACD Signal
    if last['MACD_12_26_9'] > last['MACDs_12_26_9']: buy_signals += 1
    elif last['MACD_12_26_9'] < last['MACDs_12_26_9']: sell_signals += 1

    # 4. Bollinger Bands Signal
    if last['close'] < last['BBL_20_2.0']: buy_signals += 1
    elif last['close'] > last['BBU_20_2.0']: sell_signals += 1

    # 5. Stochastic Oscillator Signal
    if last['STOCHk_14_3_3'] < 20 and last['STOCHd_14_3_3'] < 20: buy_signals += 1
    elif last['STOCHk_14_3_3'] > 80 and last['STOCHd_14_3_3'] > 80: sell_signals += 1

    # حتمی سگنل کا تعین
    final_signal = "wait"
    if buy_signals > sell_signals and buy_signals >= 3:
        final_signal = "buy"
    elif sell_signals > buy_signals and sell_signals >= 3:
        final_signal = "sell"
    # ٹائی کی صورت میں MACD کو ترجیح دیں
    elif buy_signals == sell_signals and buy_signals > 0:
        if last['MACD_12_26_9'] > last['MACDs_12_26_9']: final_signal = "buy"
        else: final_signal = "sell"
        
    return {"signal": final_signal, "details": {"buy": buy_signals, "sell": sell_signals}}

def calculate_tp_sl(candles: List[Dict[str, Any]], atr_multiplier: float = 2.0) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """
    ATR کی بنیاد پر ٹیک پرافٹ اور اسٹاپ لاس کا حساب لگاتا ہے۔
    """
    if len(candles) < 15: # ATR کے لیے کم از کم 15 پیریڈز
        return None
        
    df = pd.DataFrame(candles)
    df.ta.atr(length=14, append=True)
    
    last_close = df.iloc[-1]['close']
    atr = df.iloc[-1]['ATRr_14']
    
    if pd.isna(atr) or atr == 0:
        return None

    # Buy Signal TP/SL
    buy_tp = last_close + (atr * atr_multiplier)
    buy_sl = last_close - atr
    
    # Sell Signal TP/SL
    sell_tp = last_close - (atr * atr_multiplier)
    sell_sl = last_close + atr
    
    return ((buy_tp, buy_sl), (sell_tp, sell_sl))

# --- یہ ہے وہ گمشدہ فنکشن جسے ہم شامل کر رہے ہیں ---
def get_dynamic_atr_multiplier(risk_status: str) -> float:
    """
    مارکیٹ کے رسک کی بنیاد پر ATR ملٹی پلائر کو ایڈجسٹ کرتا ہے۔
    """
    if risk_status == "High":
        return 1.5  # زیادہ رسک میں چھوٹا ٹارگٹ
    elif risk_status == "Moderate":
        return 2.0  # درمیانے رسک میں معیاری ٹارگٹ
    else: # Low/Clear
        return 2.5  # کم رسک میں بڑا ٹارگٹ

