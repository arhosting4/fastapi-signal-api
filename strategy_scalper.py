import logging
from typing import Any, Dict, Optional

import pandas as pd
import numpy as np

from config import tech_settings
from level_analyzer import find_realistic_tp_sl

logger = logging.getLogger(__name__)

# --- تکنیکی انڈیکیٹرز کی سیٹنگز ---
EMA_SHORT_PERIOD = tech_settings.EMA_SHORT_PERIOD
EMA_LONG_PERIOD = tech_settings.EMA_LONG_PERIOD
RSI_PERIOD = tech_settings.RSI_PERIOD
SUPERTREND_ATR = tech_settings.SUPERTREND_ATR
SUPERTREND_FACTOR = tech_settings.SUPERTREND_FACTOR
BBANDS_PERIOD = tech_settings.BBANDS_PERIOD
BBANDS_STD_DEV = tech_settings.BBANDS_STD_DEV
BBANDS_SQUEEZE_THRESHOLD = tech_settings.BBANDS_SQUEEZE_THRESHOLD
ADX_PERIOD = 14 # ADX کے لیے پیریڈ

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

def calculate_bollinger_bands(data: pd.Series, period: int, std_dev: int) -> pd.DataFrame:
    middle_band = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    bandwidth = ((upper_band - lower_band) / middle_band) * 100
    return pd.DataFrame({
        'bb_upper': upper_band, 'bb_middle': middle_band,
        'bb_lower': lower_band, 'bb_bandwidth': bandwidth
    })

# ★★★ نیا، بہتر ADX فنکشن ★★★
def calculate_adx(df: pd.DataFrame, period: int) -> pd.DataFrame:
    """ADX, +DI, اور -DI کا حساب لگاتا ہے۔"""
    df_adx = pd.DataFrame()
    df_adx['H-L'] = df['high'] - df['low']
    df_adx['H-pC'] = abs(df['high'] - df['close'].shift(1))
    df_adx['L-pC'] = abs(df['low'] - df['close'].shift(1))
    df_adx['TR'] = df_adx[['H-L', 'H-pC', 'L-pC']].max(axis=1)
    
    df_adx['+DM'] = np.where((df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']), df['high'] - df['high'].shift(1), 0)
    df_adx['+DM'] = np.where(df_adx['+DM'] < 0, 0, df_adx['+DM'])
    df_adx['-DM'] = np.where((df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)), df['low'].shift(1) - df['low'], 0)
    df_adx['-DM'] = np.where(df_adx['-DM'] < 0, 0, df_adx['-DM'])
    
    ATR = df_adx['TR'].ewm(span=period, adjust=False).mean()
    df_adx['+DI'] = (df_adx['+DM'].ewm(span=period, adjust=False).mean() / ATR) * 100
    df_adx['-DI'] = (df_adx['-DM'].ewm(span=period, adjust=False).mean() / ATR) * 100
    
    DX = (abs(df_adx['+DI'] - df_adx['-DI']) / (df_adx['+DI'] + df_adx['-DI']).replace(0, 1)) * 100
    ADX = DX.ewm(span=period, adjust=False).mean()
    
    return pd.DataFrame({'adx': ADX, 'plus_di': df_adx['+DI'], 'minus_di': df_adx['-DI']})

def generate_adaptive_analysis(df: pd.DataFrame, market_regime: Dict, symbol_personality: Dict) -> Dict[str, Any]:
    regime_type = market_regime.get("regime")
    
    if len(df) < max(EMA_LONG_PERIOD, RSI_PERIOD, BBANDS_PERIOD, ADX_PERIOD, 34):
        return {"status": "no-signal", "reason": "ناکافی ڈیٹا"}

    close = df['close']
    
    # --- تمام انڈیکیٹرز کا حساب لگائیں ---
    ema_fast = close.ewm(span=EMA_SHORT_PERIOD, adjust=False).mean()
    ema_slow = close.ewm(span=EMA_LONG_PERIOD, adjust=False).mean()
    rsi = calculate_rsi(close, RSI_PERIOD)
    df = df.join(calculate_supertrend(df.copy(), SUPERTREND_ATR, SUPERTREND_FACTOR))
    df = df.join(calculate_bollinger_bands(close, BBANDS_PERIOD, BBANDS_STD_DEV))
    df = df.join(calculate_adx(df.copy(), ADX_PERIOD)) # ★★★ ADX کو شامل کیا گیا

    # آخری کینڈل کا ڈیٹا
    last = df.iloc[-1]
    
    # --- حکمت عملی 1: بریک آؤٹ ہنٹر (اسے ابھی تبدیل نہیں کیا گیا) ---
    # (یہاں بریک آؤٹ کی منطق پہلے کی طرح رہے گی)

    # --- حکمت عملی 2: ٹرینڈ فالوونگ (ADX کی نئی منطق کے ساتھ) ---
    total_score = 0
    strategy_type = "Unknown"

    if regime_type in ["Calm Trend", "Volatile Trend"]:
        strategy_type = "Trend-Following"
        
        # ★★★ ADX سمت کی نئی شرط ★★★
        is_bullish_adx = last['plus_di'] > last['minus_di']
        is_bearish_adx = last['minus_di'] > last['plus_di']
        
        is_bullish_ema = ema_fast.iloc[-1] > ema_slow.iloc[-1]
        is_bullish_supertrend = last['in_uptrend']

        # BUY سگنل کی شرائط
        if is_bullish_ema and is_bullish_supertrend and is_bullish_adx:
            total_score = 100
            core_signal = "buy"
            logger.info(f"[{df['symbol'].iloc[-1]}] Bullish Trend کی تصدیق (EMA, Supertrend, ADX+)")
        
        # SELL سگنل کی شرائط
        elif not is_bullish_ema and not is_bullish_supertrend and is_bearish_adx:
            total_score = -100
            core_signal = "sell"
            logger.info(f"[{df['symbol'].iloc[-1]}] Bearish Trend کی تصدیق (EMA, Supertrend, ADX-)")
        
        else:
            # اگر تمام شرائط پوری نہ ہوں تو کوئی سگنل نہیں
            reason = f"ADX سمت کی تصدیق نہیں ہوئی۔ +DI: {last['plus_di']:.1f}, -DI: {last['minus_di']:.1f}"
            logger.info(f"[{df['symbol'].iloc[-1]}] ٹرینڈ سگنل مسترد: {reason}")
            return {"status": "no-signal", "reason": reason}

    elif regime_type == "Ranging":
        # (رینجنگ مارکیٹ کی منطق پہلے کی طرح رہے گی)
        strategy_type = "Range-Reversal"
        if rsi.iloc[-1] > 75: total_score = -100
        elif rsi.iloc[-1] < 25: total_score = 100
        core_signal = "buy" if total_score > 0 else "sell"
    
    else:
        return {"status": "no-signal", "reason": f"مارکیٹ کا نظام '{regime_type}' ہے۔ ٹریڈنگ معطل۔"}

    if abs(total_score) == 0:
        return {"status": "no-signal", "reason": "کوئی واضح ٹریڈنگ سیٹ اپ نہیں ملا۔"}

    tp_sl_data = find_realistic_tp_sl(df, core_signal, symbol_personality)
    if not tp_sl_data:
        return {"status": "no-signal", "reason": "حقیقت پسندانہ TP/SL کا حساب نہیں لگایا جا سکا"}

    tp, sl = tp_sl_data
    
    return {
        "status": "ok", "signal": core_signal, "score": total_score,
        "price": last['close'], "tp": tp, "sl": sl, "strategy_type": strategy_type
    }
    
