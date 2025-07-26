# filename: fusion_engine.py

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session

# مقامی امپورٹس (اب strategybot نہیں ہے)
from patternai import detect_patterns
from riskguardian import check_risk
from sentinel import get_news_analysis_for_symbol
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from supply_demand import get_market_structure_analysis
from schemas import Candle

logger = logging.getLogger(__name__)

# ==============================================================================
# ★★★ اسٹریٹجی کی منطق براہ راست یہاں منتقل کر دی گئی ہے ★★★
# ==============================================================================
EMA_SHORT_PERIOD = 10
EMA_LONG_PERIOD = 30
STOCH_K = 14
STOCH_D = 3
RSI_PERIOD = 14
BBANDS_PERIOD = 20
ATR_LENGTH = 14

def calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))

def calculate_bbands(data: pd.Series, period: int) -> pd.DataFrame:
    sma = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    upper_band = sma + (std * 2)
    lower_band = sma - (std * 2)
    return pd.DataFrame({'BBl': lower_band, 'BBu': upper_band})

def calculate_stoch(high: pd.Series, low: pd.Series, close: pd.Series, k: int, d: int) -> pd.DataFrame:
    low_k = low.rolling(window=k).min()
    high_k = high.rolling(window=k).max()
    stoch_k = 100 * (close - low_k) / (high_k - low_k).replace(0, 1e-9)
    stoch_d = stoch_k.rolling(window=d).mean()
    return pd.DataFrame({'STOCHk': stoch_k, 'STOCHd': stoch_d})

def calculate_tp_sl(candles: List[Dict], signal_type: str) -> Optional[Tuple[float, float]]:
    if len(candles) < 20: return None
    df = pd.DataFrame(candles)
    df['h-l'] = df['high'] - df['low']
    df['h-pc'] = np.abs(df['high'] - df['close'].shift())
    df['l-pc'] = np.abs(df['low'] - df['close'].shift())
    tr = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    atr = tr.rolling(window=ATR_LENGTH).mean()
    if atr.empty or pd.isna(atr.iloc[-1]): return None
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
    else: return None
    return tp, sl

def generate_core_signal(candles: List[Dict]) -> Dict[str, Any]:
    if len(candles) < max(EMA_LONG_PERIOD, BBANDS_PERIOD, RSI_PERIOD):
        return {"signal": "wait", "indicators": {}}
    df = pd.DataFrame(candles)
    close = df['close']
    ema_fast = close.ewm(span=EMA_SHORT_PERIOD, adjust=False).mean()
    ema_slow = close.ewm(span=EMA_LONG_PERIOD, adjust=False).mean()
    stoch = calculate_stoch(df['high'], df['low'], close, STOCH_K, STOCH_D)
    rsi = calculate_rsi(close, RSI_PERIOD)
    bbands = calculate_bbands(close, BBANDS_PERIOD)
    if any(s.empty for s in [ema_fast, ema_slow, stoch, rsi, bbands]):
        return {"signal": "wait", "indicators": {}}
    last_close = close.iloc[-1]
    last_ema_fast = ema_fast.iloc[-1]
    last_ema_slow = ema_slow.iloc[-1]
    last_stoch_k = stoch['STOCHk'].iloc[-1]
    last_rsi = rsi.iloc[-1]
    last_bb_lower = bbands['BBl'].iloc[-1]
    last_bb_upper = bbands['BBu'].iloc[-1]
    if any(pd.isna(v) for v in [last_ema_fast, last_ema_slow, last_stoch_k, last_rsi, last_bb_lower, last_bb_upper]):
        return {"signal": "wait", "indicators": {}}
    indicators_data = {"ema_cross": "bullish" if last_ema_fast > last_ema_slow else "bearish", "stoch_k": round(last_stoch_k, 2), "rsi": round(last_rsi, 2), "price_vs_bb": "near_lower" if last_close <= last_bb_lower else ("near_upper" if last_close >= last_bb_upper else "middle")}
    buy_conditions = [last_ema_fast > last_ema_slow, last_stoch_k < 40, last_rsi > 50, last_close > last_bb_lower]
    sell_conditions = [last_ema_fast < last_ema_slow, last_stoch_k > 60, last_rsi < 50, last_close < last_bb_upper]
    if all(buy_conditions): return {"signal": "buy", "indicators": indicators_data}
    if all(sell_conditions): return {"signal": "sell", "indicators": indicators_data}
    return {"signal": "wait", "indicators": {}}
# ==============================================================================

async def generate_final_signal(db: Session, symbol: str, candles: List[Candle]) -> Dict[str, Any]:
    """
    تمام AI سگنلز کو ملا کر ایک حتمی، اعلیٰ اعتماد والا سگنل بناتا ہے۔
    """
    try:
        candle_dicts = [c.model_dump() for c in candles]
        core_signal_data = generate_core_signal(candle_dicts)
        core_signal = core_signal_data["signal"]
        indicators = core_signal_data.get("indicators", {})
        if core_signal == "wait":
            return {"status": "no-signal", "reason": "بنیادی حکمت عملی غیر جانبدار ہے۔"}
        pattern_data = detect_patterns(candle_dicts)
        risk_assessment = check_risk(candle_dicts)
        news_data = await get_news_analysis_for_symbol(symbol)
        market_structure = get_market_structure_analysis(candle_dicts)
        final_risk_status = risk_assessment.get("status", "Normal")
        if news_data.get("impact") == "High":
            final_risk_status = "Critical" if final_risk_status == "High" else "High"
        confidence = get_confidence(db, core_signal, pattern_data.get("type", "neutral"), final_risk_status, news_data.get("impact"), symbol)
        tier = get_tier(confidence, final_risk_status)
        tp_sl_data = calculate_tp_sl(candle_dicts, core_signal)
        if not tp_sl_data:
            return {"status": "no-signal", "reason": "TP/SL کا حساب نہیں لگایا جا سکا"}
        tp, sl = tp_sl_data
        reason = generate_reason(core_signal, pattern_data, final_risk_status, news_data, confidence, market_structure, indicators=indicators)
        return {"status": "ok", "symbol": symbol, "signal": core_signal, "pattern": pattern_data.get("pattern"), "risk": final_risk_status, "news": news_data.get("impact"), "reason": reason, "confidence": round(confidence, 2), "tier": tier, "timeframe": "15min", "price": candle_dicts[-1]['close'], "tp": round(tp, 5), "sl": round(sl, 5)}
    except Exception as e:
        logger.error(f"{symbol} کے لیے فیوژن انجن ناکام: {e}", exc_info=True)
        return {"status": "error", "reason": f"{symbol} کے لیے AI فیوژن میں خرابی۔"}
    
