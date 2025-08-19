# filename: strategy_scalper.py

import logging
from typing import Any, Dict, Optional, Tuple
import pandas as pd
import numpy as np

from config import tech_settings
# level_analyzer کو اب یہاں سے کال نہیں کیا جائے گا، بلکہ fusion_engine سے کیا جائے گا

logger = logging.getLogger(__name__)

# --- انڈیکیٹرز کے حساب کتاب کے فنکشنز ---
# (یہاں صرف ضروری فنکشنز رکھے گئے ہیں)
def calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    delta = data.diff(1)
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))

def calculate_supertrend(df_in: pd.DataFrame, atr_period: int, multiplier: float) -> pd.Series:
    df = df_in.copy()
    high, low, close = df['high'], df['low'], df['close']
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)
    atr = tr.ewm(alpha=1/atr_period, adjust=False).mean()
    
    df['upperband'] = (high + low) / 2 + (multiplier * atr)
    df['lowerband'] = (high + low) / 2 - (multiplier * atr)
    df['in_uptrend'] = True
    
    for i in range(1, len(df)):
        if close.iloc[i] > df['upperband'].iloc[i-1]:
            df.loc[df.index[i], 'in_uptrend'] = True
        elif close.iloc[i] < df['lowerband'].iloc[i-1]:
            df.loc[df.index[i], 'in_uptrend'] = False
        else:
            df.loc[df.index[i], 'in_uptrend'] = df['in_uptrend'].iloc[i-1]
        
        if df['in_uptrend'].iloc[i] and df['lowerband'].iloc[i] < df['lowerband'].iloc[i-1]:
            df.loc[df.index[i], 'lowerband'] = df['lowerband'].iloc[i-1]
        if not df['in_uptrend'].iloc[i] and df['upperband'].iloc[i] > df['upperband'].iloc[i-1]:
            df.loc[df.index[i], 'upperband'] = df['upperband'].iloc[i-1]
            
    return df['in_uptrend']

# --- بنیادی تجزیاتی انجن ---
def generate_adaptive_analysis(df_in: pd.DataFrame, symbol_personality: Dict) -> Dict[str, Any]:
    """
    یہ فنکشن بنیادی تکنیکی تجزیہ کرتا ہے اور ایک 'بنیادی سگنل' اور 'ٹیکنیکل اسکور' پیدا کرتا ہے۔
    یہ حتمی فیصلہ نہیں کرتا، بلکہ فیوژن انجن کو خام مال فراہم کرتا ہے۔
    """
    if len(df_in) < max(tech_settings.EMA_LONG_PERIOD, tech_settings.RSI_PERIOD):
        return {"status": "no-signal", "reason": "ناکافی ڈیٹا"}

    df = df_in.copy()
    close = df['close']
    
    # --- تمام انڈیکیٹرز کا حساب لگائیں ---
    df['ema_fast'] = close.ewm(span=tech_settings.EMA_SHORT_PERIOD, adjust=False).mean()
    df['ema_slow'] = close.ewm(span=tech_settings.EMA_LONG_PERIOD, adjust=False).mean()
    df['rsi'] = calculate_rsi(close, tech_settings.RSI_PERIOD)
    df['in_uptrend'] = calculate_supertrend(df, tech_settings.SUPERTREND_ATR, tech_settings.SUPERTREND_FACTOR)

    last = df.iloc[-1]
    
    # --- حکمت عملی کی قسم کا تعین کریں ---
    # (یہاں ہم ایک سادہ منطق استعمال کر رہے ہیں، اصل فیصلہ فیوژن انجن میں ہوگا)
    is_trending = abs(last['ema_fast'] - last['ema_slow']) > (df['close'].mean() * 0.001) # سادہ ٹرینڈ چیک
    
    core_signal = ""
    strategy_type = ""
    score = 0

    if is_trending:
        strategy_type = "Trend-Following"
        if last['ema_fast'] > last['ema_slow'] and last['in_uptrend']:
            core_signal = "buy"
            score = 80
        elif last['ema_fast'] < last['ema_slow'] and not last['in_uptrend']:
            core_signal = "sell"
            score = -80
    else: # رینجنگ
        strategy_type = "Range-Reversal"
        if last['rsi'] < 30:
            core_signal = "buy"
            score = 75
        elif last['rsi'] > 70:
            core_signal = "sell"
            score = -75

    if not core_signal:
        return {"status": "no-signal", "reason": "کوئی بنیادی تکنیکی سیٹ اپ نہیں ملا"}

    return {
        "status": "ok",
        "signal": core_signal,
        "score": score,
        "strategy_type": strategy_type
    }
    
