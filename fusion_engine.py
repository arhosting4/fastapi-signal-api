# filename: fusion_engine.py

import asyncio
import logging
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy.orm import Session

from config import api_settings, strategy_settings
from patternai import detect_patterns
from reasonbot import generate_reason
from schemas import Candle
from utils import convert_candles_to_dataframe
from level_analyzer import find_realistic_tp_sl
from regime_analyzer import get_market_regime

# --- حتمی اور درست امپورٹ ---
from strategy_scalper import get_technical_analysis

logger = logging.getLogger(__name__)

async def generate_final_signal(
    db: Session, 
    symbol: str, 
    candles: List[Candle], 
    symbol_personality: Dict
) -> Dict[str, Any]:
    """
    ایک حتمی، قابلِ عمل سگنل تیار کرتا ہے۔
    """
    try:
        df = convert_candles_to_dataframe(candles)
        if df.empty or len(df) < 50:
            return {"status": "no-signal", "reason": f"تجزیے کے لیے ناکافی ڈیٹا ({len(df)} کینڈلز)۔"}

        # مرحلہ 1: مارکیٹ کی حالت کا تعین کریں
        market_regime = get_market_regime(df)
        
        # مرحلہ 2: بنیادی تکنیکی تجزیہ حاصل کریں
        # --- حتمی اور درست فنکشن کال ---
        technical_analysis = get_technical_analysis(df, symbol)

        if technical_analysis.get("status") != "ok":
            return {"status": "no-signal", "reason": f"بنیادی تکنیکی شرط پوری نہیں ہوئی: {technical_analysis.get('reason')}"}

        core_signal = technical_analysis.get("signal")
        strategy_type = technical_analysis.get("strategy")

        # مرحلہ 3: حکمت عملی اور مارکیٹ کی حالت میں مطابقت چیک کریں
        is_compatible = False
        if market_regime in ["Calm_Trending", "Volatile_Trending"] and strategy_type == "Trend-Following":
            is_compatible = True
        elif market_regime == "Quiet_Ranging" and strategy_type == "Range-Reversal":
            is_compatible = True
        elif market_regime == "Violent_Ranging" and strategy_type == "Breakout":
            is_compatible = True
        
        if not is_compatible:
            reason = f"حکمت عملی '{strategy_type}' مارکیٹ کی حالت '{market_regime}' سے مطابقت نہیں رکھتی۔"
            logger.warning(f"透明 [{symbol}]: سگنل مسترد۔ وجہ: {reason}")
            return {"status": "no-signal", "reason": reason}

        # مرحلہ 4: اضافی تصدیق کے لیے ڈیٹا حاصل کریں
        pattern_task = asyncio.to_thread(detect_patterns, df)
        news_task = asyncio.to_thread(lambda: "Clear") # ابھی کے لیے خبروں کو نظر انداز کریں
        
        pattern_data, news_impact = await asyncio.gather(pattern_task, news_task)

        # مرحلہ 5: اعتماد کا اسکور متعین کریں
        base_confidence = 75.0
        bonus_points = 0
        pattern_type = pattern_data.get("type", "neutral")
        
        if (core_signal == "buy" and pattern_type == "bullish") or \
           (core_signal == "sell" and pattern_type == "bearish"):
            bonus_points += 10
        
        if news_impact != "High":
            bonus_points += 5
            
        confidence = min(99.0, base_confidence + bonus_points)

        # مرحلہ 6: TP/SL کا حساب لگائیں
        tp_sl_data = find_realistic_tp_sl(df, core_signal, symbol_personality, market_regime)
        if not tp_sl_data:
            return {"status": "no-signal", "reason": "حقیقت پسندانہ TP/SL کا حساب نہیں لگایا جا سکا"}
        
        tp, sl = tp_sl_data
        price = df['close'].iloc[-1]

        # مرحلہ 7: حتمی سگنل تیار کریں
        reason = generate_reason(core_signal, pattern_data, {"impact": news_impact}, confidence, strategy_type, market_regime, "A-Grade")
        
        logger.info(f"✅ [{symbol}]: سگنل منظور! اعتماد: {confidence:.1f}%, حکمت عملی: {strategy_type}, حالت: {market_regime}")

        return {
            "status": "ok", "symbol": symbol, "signal": core_signal,
            "reason": reason, "confidence": round(confidence, 2),
            "timeframe": "15min", "price": price, "tp": tp, "sl": sl,
            "strategy_type": strategy_type, "market_regime": market_regime
        }

    except Exception as e:
        logger.error(f"[{symbol}] کے لیے فیوژن انجن میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        return {"status": "error", "reason": f"AI فیوژن میں ایک غیر متوقع خرابی۔"}
