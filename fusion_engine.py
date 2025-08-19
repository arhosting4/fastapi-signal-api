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
from sentinel import get_news_analysis_for_symbol
from level_analyzer import find_realistic_tp_sl

logger = logging.getLogger(__name__)

async def generate_final_signal(
    db: Session, 
    symbol: str, 
    df: pd.DataFrame,
    technical_analysis: Dict[str, Any], # strategy_scalper سے
    market_regime: str,                 # regime_analyzer سے
    symbol_personality: Dict[str, Any]
) -> Dict[str, Any]:
    """
    یہ "فیوژن انجن 2.0" ہے۔ یہ تکنیکی تجزیے اور مارکیٹ کی حالت کو ملا کر
    ایک حتمی، قابلِ عمل سگنل تیار کرتا ہے۔
    """
    try:
        # مرحلہ 1: بنیادی تکنیکی سگنل کی جانچ
        if technical_analysis.get("status") != "ok":
            return {"status": "no-signal", "reason": f"بنیادی تکنیکی شرط پوری نہیں ہوئی: {technical_analysis.get('reason')}"}

        core_signal = technical_analysis.get("signal")
        technical_score = technical_analysis.get("score", 0)
        strategy_type = technical_analysis.get("strategy_type", "Unknown")

        # مرحلہ 2: مارکیٹ کی حالت کی بنیاد پر سگنل کی مطابقت کی جانچ
        is_match = (
            (strategy_type == "Trend-Following" and market_regime in ["Calm_Trending", "Volatile_Trending"]) or
            (strategy_type == "Range-Reversal" and market_regime == "Quiet_Ranging")
        )

        if not is_match:
            reason = f"حکمت عملی '{strategy_type}' مارکیٹ کی حالت '{market_regime}' سے مطابقت نہیں رکھتی۔"
            logger.warning(f"透明 [{symbol}]: سگنل مسترد۔ وجہ: {reason}")
            return {"status": "no-signal", "reason": reason}

        # مرحلہ 3: اضافی تصدیق کے لیے ڈیٹا حاصل کریں (پیٹرن اور خبریں)
        pattern_task = asyncio.to_thread(detect_patterns, df)
        news_task = get_news_analysis_for_symbol(symbol)
        pattern_data, news_data = await asyncio.gather(pattern_task, news_task)

        # مرحلہ 4: حتمی اعتماد کا اسکور متعین کریں
        base_confidence = 70 + ((abs(technical_score) - 35) / 65 * 20)
        
        # ریجیم کی بنیاد پر ضرب (Multiplier)
        regime_multiplier = 1.0
        if market_regime == "Calm_Trending":
            regime_multiplier = 1.15  # 15% کا بونس
        elif market_regime in ["Violent_Ranging", "No_Trade_Zone"]:
            regime_multiplier = 0.60  # 40% کی کمی
        elif market_regime == "Volatile_Trending":
            regime_multiplier = 0.90  # 10% کی کمی (احتیاط)

        # بونس اور کٹوتی
        bonus_points = 0
        if (core_signal == "buy" and pattern_data.get("type") == "bullish") or \
           (core_signal == "sell" and pattern_data.get("type") == "bearish"):
            bonus_points += 5
        
        if news_data.get("impact") != "High":
            bonus_points += 5
        else:
            bonus_points -= 15 # اعلیٰ اثر والی خبروں پر بڑی کٹوتی

        confidence = (base_confidence * regime_multiplier) + bonus_points
        confidence = min(99.0, max(0, confidence)) # اسکور کو 0-99 کی رینج میں رکھیں

        logger.info(
            f"透明 [{symbol}]: حتمی جانچ: سگنل={core_signal}, ٹیک اسکور={technical_score:.1f}, "
            f"بنیادی اعتماد={base_confidence:.1f}, ریجیم ضرب={regime_multiplier}, بونس={bonus_points}, "
            f"حتمی اعتماد={confidence:.1f}%"
        )

        if confidence < strategy_settings.FINAL_CONFIDENCE_THRESHOLD:
            return {"status": "no-signal", "reason": f"اعتماد ({confidence:.2f}%) تھریشولڈ سے کم ہے۔"}

        # مرحلہ 5: TP/SL اور وجہ بنانا
        tp_sl_data = find_realistic_tp_sl(df, core_signal, symbol_personality, strategy_type)
        if not tp_sl_data:
            return {"status": "no-signal", "reason": "حتمی TP/SL کا حساب نہیں لگایا جا سکا"}
        
        tp, sl = tp_sl_data
        signal_grade = "A-Grade" if confidence >= 85 else "B-Grade"
        
        reason = generate_reason(
            core_signal, pattern_data, news_data, confidence, 
            strategy_type, market_regime, signal_grade
        )

        logger.info(f"✅ [{symbol}]: سگنل منظور! گریڈ: {signal_grade}, اعتماد: {confidence:.1f}%, حکمت عملی: {strategy_type}")

        return {
            "status": "ok", "symbol": symbol, "signal": core_signal,
            "reason": reason, "confidence": round(confidence, 2),
            "timeframe": "15min", "price": df['close'].iloc[-1],
            "tp": round(tp, 5), "sl": round(sl, 5),
            "strategy_type": strategy_type, "signal_grade": signal_grade
        }

    except Exception as e:
        logger.error(f"[{symbol}] کے لیے فیوژن انجن میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        return {"status": "error", "reason": f"AI فیوژن میں ایک غیر متوقع خرابی۔"}
            
