# filename: scoring_engine.py

import logging
import warnings
import numpy as np
import pandas as pd
from arch import arch_model
from hurst import compute_Hc
from statsmodels.tools.sm_exceptions import ConvergenceWarning

from typing import Dict
from config import tech_settings
from level_analyzer import find_realistic_tp_sl

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

# --- یہ فنکشن اب آزاد ہے اور صحیح جگہ پر ہے ---
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
    ایک متحد اسکورنگ سسٹم کی بنیاد پر سگنل تیار کرتا ہے جس میں تکنیکی اور مقداری دونوں تجزیے شامل ہیں۔
    """
    if len(df) < 99:
        return {"status": "no-signal", "reason": f"ناکافی ڈیٹا ({len(df)})"}

    # اب یہ کال صحیح طریقے سے کام کرے گی
    df_indicators = calculate_indicators(df)
    last = df_indicators.iloc[-1]

    buy_score = 0
    sell_score = 0
    log_prefix = f"💯 [{symbol}]"

    # --- مرحلہ 1: تکنیکی اسکورنگ ---
    if last['ema_fast'] > last['ema_slow']: buy_score += 25
    else: sell_score += 25
    
    if last['in_uptrend']: buy_score += 20
    else: sell_score += 20
    
    if last['rsi'] < 35: buy_score += 15
    elif last['rsi'] > 65: sell_score += 15
    
    if last['adx'] > 25:
        if last['+DI'] > last['-DI']: buy_score += 15
        else: sell_score += 15
    
    technical_score = max(buy_score, sell_score)
    logger.info(f"{log_prefix} تکنیکی اسکور: {technical_score} (Buy: {buy_score}, Sell: {sell_score})")

    # --- مرحلہ 2: مقداری تجزیہ (بونس/پینلٹی) ---
    quantitative_modifier = 0
    try:
        close_prices = df['close']
        log_returns = np.log(close_prices / close_prices.shift(1)).dropna()
        
        hurst_exponent, _, _ = compute_Hc(close_prices, kind='price', simplified=True)
        if hurst_exponent > 0.55:
            quantitative_modifier += 15
        elif hurst_exponent < 0.48:
            quantitative_modifier -= 10
        
        scaled_returns = log_returns * 100
        model = arch_model(scaled_returns, p=1, q=1, rescale=False)
        results = model.fit(disp="off")
        forecast = results.forecast(horizon=1)
        predicted_vol = np.sqrt(forecast.variance.iloc[-1, 0]) / 100
        historical_vol = log_returns.tail(20).std()
        
        if predicted_vol < historical_vol:
            quantitative_modifier += 10
        elif predicted_vol > (historical_vol * 1.8):
            quantitative_modifier -= 15

        logger.info(f"{log_prefix} مقداری موڈیفائر: {quantitative_modifier} (Hurst: {hurst_exponent:.2f})")
    except Exception as e:
        logger.warning(f"{log_prefix} مقداری تجزیہ میں خرابی: {e}")
        quantitative_modifier = 0

    # --- مرحلہ 3: حتمی فیصلہ ---
    final_score = technical_score + quantitative_modifier
    
    if final_score < 75:
        logger.info(f"{log_prefix} ❌ حتمی اسکور ({final_score}) حد (75) سے کم ہے۔ کوئی سگنل نہیں۔")
        return {"status": "no-signal", "reason": f"حتمی اسکور ({final_score}) حد سے کم ہے۔"}

    signal_type = "buy" if buy_score > sell_score else "sell"
    
    tp_sl_data = find_realistic_tp_sl(df, signal_type, symbol_personality, "Calm_Trending")
    if not tp_sl_data:
        return {"status": "no-signal", "reason": "TP/SL کا حساب نہیں لگایا جا سکا"}
    
    tp, sl = tp_sl_data
    price = df['close'].iloc[-1]
    
    reason = f"A {signal_type.upper()} signal with score {final_score} was generated. Tech Score: {technical_score}, Quant Modifier: {quantitative_modifier}."
    logger.info(f"✅ [{symbol}]: سگنل منظور! قسم: {signal_type.upper()}, حتمی اسکور: {final_score}")

    return {
        "status": "ok", "symbol": symbol, "signal": signal_type,
        "reason": reason, "confidence": final_score,
        "timeframe": "15min", "price": price, "tp": tp, "sl": sl
    }
    
