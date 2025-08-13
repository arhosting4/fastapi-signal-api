# filename: strategy_scalper.py

import logging
from typing import Any, Dict, Optional

import pandas as pd

from config import tech_settings
from level_analyzer import find_realistic_tp_sl

logger = logging.getLogger(__name__)

# === پروجیکٹ فینکس: tech_settings سے پیرامیٹرز درآمد کرنا ===
EMA_SHORT_PERIOD = tech_settings.EMA_SHORT_PERIOD
EMA_LONG_PERIOD = tech_settings.EMA_LONG_PERIOD
RSI_PERIOD = tech_settings.RSI_PERIOD
SUPERTREND_ATR = tech_settings.SUPERTREND_ATR
SUPERTREND_FACTOR = tech_settings.SUPERTREND_FACTOR

def calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    delta = data.diff(1)
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def calculate_supertrend(df: pd.DataFrame, atr_period: int, multiplier: float) -> pd.DataFrame:
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
    return df

def generate_adaptive_analysis(df: pd.DataFrame, market_regime: Dict, symbol_personality: Dict) -> Dict[str, Any]:
    """
    مارکیٹ کے نظام کی بنیاد پر انکولی حکمت عملی کا استعمال کرتے ہوئے تکنیکی تجزیہ کرتا ہے۔
    """
    regime_type = market_regime.get("regime")
    
    if len(df) < max(EMA_LONG_PERIOD, RSI_PERIOD, 34):
        return {"status": "no-signal", "reason": "ناکافی ڈیٹا"}

    close = df['close']
    ema_fast = close.ewm(span=EMA_SHORT_PERIOD, adjust=False).mean()
    ema_slow = close.ewm(span=EMA_LONG_PERIOD, adjust=False).mean()
    rsi = calculate_rsi(close, RSI_PERIOD)
    df_supertrend = calculate_supertrend(df.copy(), SUPERTREND_ATR, SUPERTREND_FACTOR)
    
    last_ema_fast, last_ema_slow = ema_fast.iloc[-1], ema_slow.iloc[-1]
    last_rsi = rsi.iloc[-1]
    in_uptrend = df_supertrend['in_uptrend'].iloc[-1]
    
    total_score = 0
    strategy_type = "Unknown"

    # === پروجیکٹ فینکس: درست حکمت عملی کا انتخاب ===
    if regime_type in ["Calm Trend", "Volatile Trend"]:
        strategy_type = "Trend-Following"
        ema_score = 1 if last_ema_fast > last_ema_slow else -1
        supertrend_score = 1 if in_uptrend else -1
        total_score = (ema_score * 0.5) + (supertrend_score * 0.5)
        total_score *= 100
    
    elif regime_type == "Ranging":
        strategy_type = "Range-Reversal"
        if last_rsi > 70: total_score = -100 # Overbought
        elif last_rsi < 30: total_score = 100 # Oversold
    
    else: # Kill Zone
        return {"status": "no-signal", "reason": f"مارکیٹ کا نظام 'Kill Zone' ہے۔ ٹریڈنگ معطل۔"}

    # بنیادی سگنل کی شرط
    if abs(total_score) < 35:
        return {"status": "no-signal", "reason": f"تکنیکی اسکور ({total_score:.1f}) تھریشولڈ سے کم ہے۔"}

    core_signal = "buy" if total_score > 0 else "sell"
    
    # TP/SL کا حساب
    tp_sl_data = find_realistic_tp_sl(df, core_signal, symbol_personality)
    if not tp_sl_data:
        return {"status": "no-signal", "reason": "حقیقت پسندانہ TP/SL کا حساب نہیں لگایا جا سکا"}

    tp, sl = tp_sl_data
    
    indicators_data = {
        "ema_fast": round(last_ema_fast, 5), "ema_slow": round(last_ema_slow, 5),
        "rsi": round(last_rsi, 2),
        "supertrend_direction": "Up" if in_uptrend else "Down",
    }
    
    return {
        "status": "ok",
        "signal": core_signal,
        "score": total_score,
        "price": close.iloc[-1],
        "tp": tp,
        "sl": sl,
        "indicators": indicators_data,
        "strategy_type": strategy_type
    }
    
