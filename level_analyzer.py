import logging
from typing import Dict, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# ==============================================================================
# ماڈل 1: رینج ٹریڈنگ کے لیے سپلائی/ڈیمانڈ
# ==============================================================================
def find_supply_demand_zones(df: pd.DataFrame, window: int = 100) -> Dict[str, Optional[Tuple[float, float]]]:
    # ... (یہ فنکشن پچھلے جواب سے بغیر تبدیلی کے لیا گیا ہے)
    recent_df = df.tail(window)
    atr = (recent_df['high'] - recent_df['low']).ewm(span=14).mean().iloc[-1]
    demand_zone, supply_zone = None, None
    rally_candles = recent_df[ (recent_df['close'] - recent_df['open']) > atr ]
    if not rally_candles.empty:
        base_candle = recent_df.loc[rally_candles.index[-1] - 1] if rally_candles.index[-1] - 1 in recent_df.index else None
        if base_candle is not None: demand_zone = (base_candle['high'], base_candle['low'])
    drop_candles = recent_df[ (recent_df['open'] - recent_df['close']) > atr ]
    if not drop_candles.empty:
        base_candle = recent_df.loc[drop_candles.index[-1] - 1] if drop_candles.index[-1] - 1 in recent_df.index else None
        if base_candle is not None: supply_zone = (base_candle['high'], base_candle['low'])
    return {"supply": supply_zone, "demand": demand_zone}

def calculate_range_tp_sl(df: pd.DataFrame, signal_type: str, symbol_personality: Dict) -> Optional[Tuple[float, float]]:
    last_close = df['close'].iloc[-1]
    zones = find_supply_demand_zones(df)
    demand_zone, supply_zone = zones.get("demand"), zones.get("supply")
    if not demand_zone or not supply_zone: return None
    
    equilibrium = (supply_zone[0] + demand_zone[1]) / 2
    take_profit, stop_loss = None, None

    if signal_type == 'buy' and last_close < equilibrium:
        stop_loss, take_profit = demand_zone[1], supply_zone[1]
    elif signal_type == 'sell' and last_close > equilibrium:
        stop_loss, take_profit = supply_zone[0], demand_zone[0]
    else:
        return None

    min_rr = symbol_personality.get("rr_calm", 1.0)
    risk = abs(last_close - stop_loss)
    reward = abs(take_profit - last_close)
    if risk == 0 or (reward / risk) < min_rr: return None
    
    return take_profit, stop_loss

# ==============================================================================
# ماڈل 2: رجحان کی پیروی (Trend Following)
# ==============================================================================
def calculate_trend_tp_sl(df: pd.DataFrame, signal_type: str, symbol_personality: Dict) -> Optional[Tuple[float, float]]:
    last_close = df['close'].iloc[-1]
    atr = (df['high'] - df['low']).ewm(span=14).mean().iloc[-1]
    
    # SL کا تعین: حالیہ سوئنگ لو/ہائی کے پیچھے
    recent_swings = df.tail(20)
    stop_loss = None
    if signal_type == 'buy':
        swing_low = recent_swings['low'].min()
        stop_loss = swing_low - (atr * 0.2)
    else: # sell
        swing_high = recent_swings['high'].max()
        stop_loss = swing_high + (atr * 0.2)

    # TP کا تعین: مقررہ RR کی بنیاد پر
    min_rr = symbol_personality.get("rr_volatile", 1.5)
    risk = abs(last_close - stop_loss)
    if risk == 0: return None
    
    take_profit = last_close + (risk * min_rr) if signal_type == 'buy' else last_close - (risk * min_rr)
    
    return take_profit, stop_loss

# ==============================================================================
# مرکزی فنکشن: جو مارکیٹ کی حالت کا تعین کرتا ہے
# ==============================================================================
def find_market_state_and_get_tp_sl(df: pd.DataFrame, signal_type: str, symbol_personality: Dict) -> Optional[Tuple[float, float]]:
    """
    مارکیٹ کی حالت (رجحان یا رینج) کا تعین کرتا ہے اور مناسب TP/SL حکمت عملی کا انتخاب کرتا ہے۔
    """
    # 1. مارکیٹ کی حالت کا تعین کریں
    ema_20 = df['close'].ewm(span=20, adjust=False).mean()
    ema_50 = df['close'].ewm(span=50, adjust=False).mean()
    last_close = df['close'].iloc[-1]
    
    market_state = "Ranging"
    if last_close > ema_20.iloc[-1] and ema_20.iloc[-1] > ema_50.iloc[-1]:
        market_state = "Uptrend"
    elif last_close < ema_20.iloc[-1] and ema_20.iloc[-1] < ema_50.iloc[-1]:
        market_state = "Downtrend"

    logger.info(f"مارکیٹ کی حالت کی تشخیص: {market_state}")

    # 2. مناسب حکمت عملی منتخب کریں
    if market_state == "Uptrend" and signal_type == 'buy':
        logger.info("رجحان کی حکمت عملی (Trend Strategy) فعال کی گئی۔")
        return calculate_trend_tp_sl(df, signal_type, symbol_personality)
    elif market_state == "Downtrend" and signal_type == 'sell':
        logger.info("رجحان کی حکمت عملی (Trend Strategy) فعال کی گئی۔")
        return calculate_trend_tp_sl(df, signal_type, symbol_personality)
    elif market_state == "Ranging":
        logger.info("رینج کی حکمت عملی (Range Strategy) فعال کی گئی۔")
        return calculate_range_tp_sl(df, signal_type, symbol_personality)
    else:
        logger.info(f"سگنل ({signal_type}) مارکیٹ کی حالت ({market_state}) سے مطابقت نہیں رکھتا۔ مسترد۔")
        return None
                          
