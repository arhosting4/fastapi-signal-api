import pandas_ta as ta
import pandas as pd
import numpy as np

def generate_core_signal(symbol: str, tf: str, closes: list) -> str:
    """
    Generates a core trading signal based on multiple technical indicators.
    """
    if len(closes) < 52: # Ichimoku کو 52 پیریڈز کی ضرورت ہوتی ہے
        return "wait"

    close_series = pd.Series(closes)

    # --- انڈیکیٹر کا حساب ---
    sma_short = ta.sma(close_series, length=10)
    sma_long = ta.sma(close_series, length=30)
    rsi = ta.rsi(close_series, length=14)
    macd = ta.macd(close_series, fast=12, slow=26, signal=9)
    bbands = ta.bbands(close_series, length=20, std=2.0)
    stoch = ta.stoch(high=close_series, low=close_series, close=close_series, k=14, d=3, smooth_k=3)
    
    # *** اہم تبدیلی: Ichimoku Cloud کا حساب ***
    # pandas_ta ہمیں ایک مکمل DataFrame دیتا ہے
    ichimoku_df = ta.ichimoku(high=close_series, low=close_series, close=close_series, tenkan=9, kijun=26, senkou=52)
    
    # DataFrame سے تازہ ترین ویلیوز حاصل کریں
    latest_ichimoku = ichimoku_df.iloc[-1]
    # بادل کی بالائی اور نچلی حدود
    senkou_a = latest_ichimoku['ISA_9_26_52']
    senkou_b = latest_ichimoku['ISB_26_52']
    # Tenkan-sen اور Kijun-sen
    tenkan_sen = latest_ichimoku['ITS_9']
    kijun_sen = latest_ichimoku['IKS_26']


    buy_signals = 0
    sell_signals = 0

    # 1. SMA Crossover
    if not pd.isna(sma_short.iloc[-1]) and not pd.isna(sma_long.iloc[-1]):
        if sma_short.iloc[-1] > sma_long.iloc[-1]: buy_signals += 1
        elif sma_short.iloc[-1] < sma_long.iloc[-1]: sell_signals += 1

    # 2. RSI
    if not pd.isna(rsi.iloc[-1]):
        if rsi.iloc[-1] < 30: buy_signals += 1
        elif rsi.iloc[-1] > 70: sell_signals += 1

    # 3. MACD
    if macd is not None and not macd.empty:
        if macd[f'MACD_12_26_9'].iloc[-1] > macd[f'MACDs_12_26_9'].iloc[-1]: buy_signals += 1
        elif macd[f'MACD_12_26_9'].iloc[-1] < macd[f'MACDs_12_26_9'].iloc[-1]: sell_signals += 1

    # 4. Bollinger Bands
    if bbands is not None and not bbands.empty:
        if close_series.iloc[-1] < bbands[f'BBL_20_2.0'].iloc[-1]: buy_signals += 1
        elif close_series.iloc[-1] > bbands[f'BBU_20_2.0'].iloc[-1]: sell_signals += 1

    # 5. Stochastic Oscillator
    if stoch is not None and not stoch.empty:
        if stoch[f'STOCHk_14_3_3'].iloc[-1] < 20: buy_signals += 1
        elif stoch[f'STOCHk_14_3_3'].iloc[-1] > 80: sell_signals += 1

    # *** اہم تبدیلی: Ichimoku Cloud کی منطق ***
    # ہم Ichimoku کو زیادہ اہمیت دیں گے، اس لیے 2 پوائنٹس دیں گے
    if not pd.isna(senkou_a) and not pd.isna(senkou_b) and not pd.isna(tenkan_sen) and not pd.isna(kijun_sen):
        # مضبوط تیزی کا سگنل: قیمت بادل سے اوپر اور Tenkan, Kijun سے اوپر
        if close_series.iloc[-1] > senkou_a and close_series.iloc[-1] > senkou_b:
            buy_signals += 2
        # مضبوط مندی کا سگنل: قیمت بادل سے نیچے اور Tenkan, Kijun سے نیچے
        elif close_series.iloc[-1] < senkou_a and close_series.iloc[-1] < senkou_b:
            sell_signals += 2
        
        # Tenkan/Kijun کراس اوور
        # ہمیں پچھلی کینڈل کا ڈیٹا بھی چاہیے
        prev_ichimoku = ichimoku_df.iloc[-2]
        prev_tenkan_sen = prev_ichimoku['ITS_9']
        prev_kijun_sen = prev_ichimoku['IKS_26']
        if tenkan_sen > kijun_sen and prev_tenkan_sen <= prev_kijun_sen:
            buy_signals += 1 # تیزی کا کراس اوور
        elif tenkan_sen < kijun_sen and prev_tenkan_sen >= prev_kijun_sen:
            sell_signals += 1 # مندی کا کراس اوور


    # --- حتمی فیصلہ ---
    # اب ہم 3 سگنلز کا تقاضا کریں گے کیونکہ کل پوائنٹس بڑھ گئے ہیں
    if buy_signals > sell_signals and buy_signals >= 3:
        return "buy"
    elif sell_signals > buy_signals and sell_signals >= 3:
        return "sell"
    else:
        return "wait"

def calculate_tp_sl(signal: str, price: float, highs: list, lows: list) -> dict:
    if not highs or not lows: return {"tp": None, "sl": None}
    
    high_series = pd.Series(highs)
    low_series = pd.Series(lows)
    close_series = pd.Series(highs + lows) # ATR کے لیے
    
    atr = ta.atr(high_series, low_series, close_series, length=14)
    if atr is None or atr.empty or pd.isna(atr.iloc[-1]):
        return {"tp": None, "sl": None}
        
    atr_value = atr.iloc[-1]
    
    if signal == "buy":
        tp = price + (atr_value * 2)
        sl = price - (atr_value * 1.5)
        return {"tp": tp, "sl": sl}
    elif signal == "sell":
        tp = price - (atr_value * 2)
        sl = price + (atr_value * 1.5)
        return {"tp": tp, "sl": sl}
    else:
        return {"tp": None, "sl": None}
        
