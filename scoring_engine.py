# filename: scoring_engine.py

import logging
import warnings
import numpy as np
import pandas as pd
from arch import arch_model
from hurst import compute_Hc
from statsmodels.tools.sm_exceptions import ConvergenceWarning

from config import tech_settings
from level_analyzer import find_realistic_tp_sl

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

# --- حساب کتاب کے بنیادی فنکشنز ---
def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """تمام ضروری انڈیکیٹرز کا حساب لگاتا ہے اور انہیں DataFrame میں شامل کرتا ہے۔"""
    df_out = df.copy()
    close = df_out['close']
    
    # تکنیکی انڈیکیٹرز
    df_out['ema_fast'] = close.ewm(span=tech_settings.EMA_SHORT_PERIOD, adjust=False).mean()
    df_out['ema_slow'] = close.ewm(span=tech_settings.EMA_LONG_PERIOD, adjust=False).mean()
    
    delta = close.diff(1)
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    avg_gain = gain.ewm(com=tech_settings.RSI_PERIOD - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=tech_settings.RSI_PERIOD - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    df_out['rsi'] = 100 - (100 / (1 + rs))
    
    high, low = df_out['high'], df_out['low']
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/tech_settings.SUPERTREND_ATR, adjust=False).mean()
    df_out['upperband'] = (high + low) / 2 + (tech_settings.SUPERTREND_FACTOR * atr)
    df_out['lowerband'] = (high + low) / 2 - (tech_settings.SUPERTREND_FACTOR * atr)
    df_out['in_uptrend'] = True
    for i in range(1, len(df_out)):
        if close.iloc[i] > df_out['upperband'].iloc[i-1]:
            df_out.loc[df_out.index[i], 'in_uptrend'] = True
        elif close.iloc[i] < df_out['lowerband'].iloc[i-1]:
            df_out.loc[df_out.index[i], 'in_uptrend'] = False
        else:
            df_out.loc[df_out.index[i], 'in_uptrend'] = df_out['in_uptrend'].iloc[i-1]
    
    # ADX
    plus_dm = np.where((high - high.shift(1)) > (low.shift(1) - low), high - high.shift(1), 0)
    minus_dm = np.where((low.shift(1) - low) > (high - high.shift(1)), low.shift(1) - low, 0)
    df_out['+DM'] = np.where(plus_dm < 0, 0, plus_dm)
    df_out['-DM'] = np.where(minus_dm < 0, 0, minus_dm)
    ATR = tr.ewm(span=14, adjust=False).mean()
    df_out['+DI'] = (df_out['+DM'].ewm(span=14, adjust=False).mean() / ATR) * 100
    df_out['-DI'] = (df_out['-DM'].ewm(span=14, adjust=False).mean() / ATR) * 100
    DX = (abs(df_out['+DI'] - df_out['-DI']) / (df_out['+DI'] + df_out['-DI']).replace(0, 1)) * 100
    df_out['adx'] = DX.ewm(span=14, adjust=False).mean()

    return df_out

# --- مرکزی اسکورنگ فنکشن ---
def get_scored_signal(df: pd.DataFrame, symbol: str, symbol_personality: Dict) -> Dict:
    """
    ایک متحد اسکورنگ سسٹم کی بنیاد پر سگنل تیار کرتا ہے۔
    """
    if len(df) < 50:
        return {"status": "no-signal", "reason": "ناکافی ڈیٹا"}

    df_indicators = calculate_indicators(df)
    last = df_indicators.iloc[-1]

    buy_score = 0
    sell_score = 0
    
    log_prefix = f"💯 [{symbol}]"

    # 1. EMA کراس اوور اسکور
    if last['ema_fast'] > last['ema_slow']:
        buy_score += 25
    else:
        sell_score += 25
    logger.info(f"{log_prefix} EMA Score: Buy={buy_score}, Sell={sell_score}")

    # 2. Supertrend اسکور
    if last['in_uptrend']:
        buy_score += 20
    else:
        sell_score += 20
    logger.info(f"{log_prefix} Supertrend Score: Buy={buy_score}, Sell={sell_score}")

    # 3. RSI اسکور
    if last['rsi'] < 35:
        buy_score += 15
    elif last['rsi'] > 65:
        sell_score += 15
    logger.info(f"{log_prefix} RSI Score: Buy={buy_score}, Sell={sell_score}")

    # 4. ADX ٹرینڈ کی طاقت کا اسکور
    if last['adx'] > 25:
        if last['+DI'] > last['-DI']:
            buy_score += 15
        else:
            sell_score += 15
    logger.info(f"{log_prefix} ADX Score: Buy={buy_score}, Sell={sell_score}")

    # حتمی فیصلہ
    final_score = max(buy_score, sell_score)
    
    if final_score < 70: # سگنل کے لیے کم از کم حد
        logger.info(f"{log_prefix} ❌ حتمی اسکور ({final_score}) حد (70) سے کم ہے۔ کوئی سگنل نہیں۔")
        return {"status": "no-signal", "reason": f"حتمی اسکور ({final_score}) حد سے کم ہے۔"}

    signal_type = "buy" if buy_score > sell_score else "sell"
    
    # TP/SL کا حساب
    tp_sl_data = find_realistic_tp_sl(df, signal_type, symbol_personality, "Calm_Trending") # ڈیفالٹ حالت
    if not tp_sl_data:
        return {"status": "no-signal", "reason": "TP/SL کا حساب نہیں لگایا جا سکا"}
    
    tp, sl = tp_sl_data
    price = df['close'].iloc[-1]
    
    reason = f"A {signal_type.upper()} signal was generated with a confidence score of {final_score} based on a confluence of technical indicators."

    logger.info(f"✅ [{symbol}]: سگنل منظور! قسم: {signal_type.upper()}, اسکور: {final_score}")

    return {
        "status": "ok", "symbol": symbol, "signal": signal_type,
        "reason": reason, "confidence": final_score,
        "timeframe": "15min", "price": price, "tp": tp, "sl": sl
    }
    
