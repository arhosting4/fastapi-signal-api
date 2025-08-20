# filename: strategy_scalper.py

import logging
from typing import Any, Dict

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
ADX_PERIOD = 14

# --- حساب کتاب کے فنکشنز (پہلے جیسے ہی) ---
def calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    delta = data.diff(1)
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))

def calculate_supertrend(df_in: pd.DataFrame, atr_period: int, multiplier: float) -> pd.DataFrame:
    df = df_in.copy()
    high, low, close = df['high'], df['low'], df['close']
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
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
    return df[['upperband', 'lowerband', 'in_uptrend']]

def calculate_bollinger_bands(data: pd.Series, period: int, std_dev: int) -> pd.DataFrame:
    middle_band = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    bandwidth = ((upper_band - lower_band) / middle_band) * 100
    return pd.DataFrame({'bb_upper': upper_band, 'bb_middle': middle_band, 'bb_lower': lower_band, 'bb_bandwidth': bandwidth})

def calculate_adx(df_in: pd.DataFrame, period: int) -> pd.DataFrame:
    df = df_in.copy()
    df_adx = pd.DataFrame(index=df.index)
    df_adx['H-L'] = df['high'] - df['low']
    df_adx['H-pC'] = abs(df['high'] - df['close'].shift(1))
    df_adx['L-pC'] = abs(df['low'] - df['close'].shift(1))
    df_adx['TR'] = df_adx[['H-L', 'H-pC', 'L-pC']].max(axis=1)
    df_adx['+DM'] = np.where((df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']), df['high'] - df['high'].shift(1), 0)
    df_adx['+DM'][df_adx['+DM'] < 0] = 0
    df_adx['-DM'] = np.where((df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)), df['low'].shift(1) - df['low'], 0)
    df_adx['-DM'][df_adx['-DM'] < 0] = 0
    ATR = df_adx['TR'].ewm(span=period, adjust=False).mean()
    df_adx['+DI'] = (df_adx['+DM'].ewm(span=period, adjust=False).mean() / ATR) * 100
    df_adx['-DI'] = (df_adx['-DM'].ewm(span=period, adjust=False).mean() / ATR) * 100
    DX = (abs(df_adx['+DI'] - df_adx['-DI']) / (df_adx['+DI'] + df_adx['-DI']).replace(0, 1)) * 100
    ADX = DX.ewm(span=period, adjust=False).mean()
    return pd.DataFrame({'adx': ADX, 'plus_di': df_adx['+DI'], 'minus_di': df_adx['-DI']})

# --- مرکزی تجزیاتی فنکشن (شفاف لاگنگ کے ساتھ) ---
def get_technical_analysis(df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """
    مختلف تکنیکی انڈیکیٹرز کی بنیاد پر ایک بنیادی سگنل اور اس کی وجہ فراہم کرتا ہے۔
    یہ فنکشن اب ہر قدم پر تفصیلی لاگنگ فراہم کرے گا۔
    """
    if len(df) < max(EMA_LONG_PERIOD, RSI_PERIOD, BBANDS_PERIOD, ADX_PERIOD, 34):
        return {"status": "no-signal", "reason": "تکنیکی تجزیے کے لیے ناکافی ڈیٹا"}

    close = df['close']
    
    # --- تمام انڈیکیٹرز کا حساب لگائیں ---
    df = df.join(calculate_supertrend(df, SUPERTREND_ATR, SUPERTREND_FACTOR))
    df = df.join(calculate_adx(df, ADX_PERIOD))
    df['ema_fast'] = close.ewm(span=EMA_SHORT_PERIOD, adjust=False).mean()
    df['ema_slow'] = close.ewm(span=EMA_LONG_PERIOD, adjust=False).mean()
    df['rsi'] = calculate_rsi(close, RSI_PERIOD)
    df = df.join(calculate_bollinger_bands(close, BBANDS_PERIOD, BBANDS_STD_DEV))

    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # --- لاگنگ کے لیے متغیرات ---
    log_prefix = f"🛠️ [{symbol}]"
    
    # --- حکمت عملی 1: ٹرینڈ فالوونگ (Trend-Following) ---
    is_bullish_ema = last['ema_fast'] > last['ema_slow']
    is_bearish_ema = last['ema_fast'] < last['ema_slow']
    is_bullish_supertrend = last['in_uptrend']
    is_bearish_supertrend = not last['in_uptrend']
    is_trending_adx = last['adx'] > 25
    
    logger.info(f"{log_prefix} ٹرینڈ جانچ: EMA Fast > Slow? {'ہاں' if is_bullish_ema else 'نہیں'} | Supertrend Bullish? {'ہاں' if is_bullish_supertrend else 'نہیں'} | ADX > 25? {'ہاں' if is_trending_adx else 'نہیں'}")

    if is_trending_adx:
        if is_bullish_ema and is_bullish_supertrend:
            logger.info(f"{log_prefix} ✅ ٹرینڈ حکمت عملی: Bullish سگنل ملا۔")
            return {"status": "ok", "signal": "buy", "strategy": "Trend-Following"}
        if is_bearish_ema and is_bearish_supertrend:
            logger.info(f"{log_prefix} ✅ ٹرینڈ حکمت عملی: Bearish سگنل ملا۔")
            return {"status": "ok", "signal": "sell", "strategy": "Trend-Following"}

    # --- حکمت عملی 2: رینج ریورسل (Range-Reversal) ---
    is_ranging_adx = last['adx'] < 20
    is_rsi_oversold = last['rsi'] < 30
    is_rsi_overbought = last['rsi'] > 70
    
    logger.info(f"{log_prefix} رینج جانچ: ADX < 20? {'ہاں' if is_ranging_adx else 'نہیں'} | RSI Oversold (<30)? {'ہاں' if is_rsi_oversold else 'نہیں'} | RSI Overbought (>70)? {'ہاں' if is_rsi_overbought else 'نہیں'}")

    if is_ranging_adx:
        if is_rsi_oversold:
            logger.info(f"{log_prefix} ✅ رینج حکمت عملی: Bullish (Oversold) سگنل ملا۔")
            return {"status": "ok", "signal": "buy", "strategy": "Range-Reversal"}
        if is_rsi_overbought:
            logger.info(f"{log_prefix} ✅ رینج حکمت عملی: Bearish (Overbought) سگنل ملا۔")
            return {"status": "ok", "signal": "sell", "strategy": "Range-Reversal"}

    # --- حکمت عملی 3: بریک آؤٹ (Breakout) ---
    is_squeezing = prev['bb_bandwidth'] < (df['bb_bandwidth'].rolling(50).mean() * 0.6) # اگر بینڈ کی چوڑائی پچھلے 50 کینڈلز کی اوسط سے 60% کم ہو
    is_breakout_up = last['close'] > last['bb_upper']
    is_breakout_down = last['close'] < last['bb_lower']

    logger.info(f"{log_prefix} بریک آؤٹ جانچ: Squeeze? {'ہاں' if is_squeezing else 'نہیں'} | Breakout Up? {'ہاں' if is_breakout_up else 'نہیں'} | Breakout Down? {'ہاں' if is_breakout_down else 'نہیں'}")

    if is_squeezing:
        if is_breakout_up:
            logger.info(f"{log_prefix} ✅ بریک آؤٹ حکمت عملی: Bullish سگنل ملا۔")
            return {"status": "ok", "signal": "buy", "strategy": "Breakout"}
        if is_breakout_down:
            logger.info(f"{log_prefix} ✅ بریک آؤٹ حکمت عملی: Bearish سگنل ملا۔")
            return {"status": "ok", "signal": "sell", "strategy": "Breakout"}

    logger.info(f"{log_prefix} ❌ کوئی واضح تکنیکی سیٹ اپ نہیں ملا۔")
    return {"status": "no-signal", "reason": "کوئی بنیادی تکنیکی سیٹ اپ نہیں ملا"}
    
