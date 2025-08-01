# filename: level_analyzer.py

import logging
import pandas as pd
from typing import List, Dict, Optional, Tuple
from config import STRATEGY

logger = logging.getLogger(__name__)

# کنفیگریشن ویلیوز
MIN_RISK_REWARD_RATIO = STRATEGY.get("MIN_RISK_REWARD_RATIO", 1.2)
MIN_CONFLUENCE_SCORE = STRATEGY.get("MIN_CONFLUENCE_SCORE", 4)
LEVEL_SCORING_WEIGHTS = STRATEGY.get("LEVEL_SCORING_WEIGHTS", {
    "pivots": 3,
    "swings": 2,
    "fibonacci": 2,
    "psychological": 1
})

def _calculate_pivot_points(df: pd.DataFrame) -> Dict[str, float]:
    last_candle = df.iloc[-1]
    high, low, close = last_candle['high'], last_candle['low'], last_candle['close']
    pivot = (high + low + close) / 3
    return {
        'p': pivot,
        'r1': (2 * pivot) - low,
        's1': (2 * pivot) - high,
        'r2': pivot + (high - low),
        's2': pivot - (high - low),
    }

def _find_swing_levels(df: pd.DataFrame, window: int = 10) -> Dict[str, List[float]]:
    highs = df['high'].rolling(window=window, center=True).max().dropna().unique()
    lows = df['low'].rolling(window=window, center=True).min().dropna().unique()
    return {
        "highs": sorted(list(highs), reverse=True)[:3],
        "lows": sorted(list(lows))[:3]
    }

def _get_fibonacci_levels(df: pd.DataFrame) -> Dict[str, float]:
    recent_high = df['high'].tail(34).max()
    recent_low = df['low'].tail(34).min()
    price_range = recent_high - recent_low
    if price_range == 0: return {}
    return {
        'fib_23_6': recent_high - (price_range * 0.236),
        'fib_38_2': recent_high - (price_range * 0.382),
        'fib_50_0': recent_high - (price_range * 0.5),
        'fib_61_8': recent_high - (price_range * 0.618),
    }

def _get_psychological_levels(df: pd.DataFrame) -> List[float]:
    close = df['close'].iloc[-1]
    base = round(close, -1)
    return [base - 50, base, base + 50]

def _score_level(level: float, current_price: float, source: str) -> float:
    score = LEVEL_SCORING_WEIGHTS.get(source, 1)
    proximity = 1 - (abs(current_price - level) / current_price)
    return score * proximity

def find_optimal_tp_sl(df: pd.DataFrame) -> Dict[str, Optional[float]]:
    try:
        current_price = df['close'].iloc[-1]
        pivot_levels = _calculate_pivot_points(df)
        swing_levels = _find_swing_levels(df)
        fib_levels = _get_fibonacci_levels(df)
        psych_levels = _get_psychological_levels(df)

        all_levels = []

        for name, lvl in pivot_levels.items():
            all_levels.append(("pivots", lvl))
        for lvl in swing_levels['highs'] + swing_levels['lows']:
            all_levels.append(("swings", lvl))
        for name, lvl in fib_levels.items():
            all_levels.append(("fibonacci", lvl))
        for lvl in psych_levels:
            all_levels.append(("psychological", lvl))

        scored = []
        for source, lvl in all_levels:
            score = _score_level(lvl, current_price, source)
            scored.append((lvl, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        tp = next((lvl for lvl, score in scored if lvl > current_price and score >= MIN_CONFLUENCE_SCORE), None)
        sl = next((lvl for lvl, score in scored if lvl < current_price and score >= MIN_CONFLUENCE_SCORE), None)

        if tp and sl:
            rr_ratio = (tp - current_price) / (current_price - sl)
            if rr_ratio < MIN_RISK_REWARD_RATIO:
                logger.info(f"⚠️ R:R {rr_ratio:.2f} is less than minimum acceptable.")
                return {"tp": None, "sl": None}

        return {"tp": round(tp, 2) if tp else None, "sl": round(sl, 2) if sl else None}
    except Exception as e:
        logger.error(f"❌ TP/SL نکالنے میں خرابی: {e}", exc_info=True)
        return {"tp": None, "sl": None}
