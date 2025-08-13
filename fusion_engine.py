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
from utils import convert_candles_to_dataframe
from strategy_scalper import generate_adaptive_analysis

logger = logging.getLogger(__name__)

async def generate_final_signal(
    db: Session, 
    symbol: str, 
    candles: List[Candle], 
    market_regime: str,
    symbol_personality: Dict
) -> Dict[str, Any]:
    """
    ایک حتمی، قابلِ عمل سگنل تیار کرتا ہے۔
    یہ "پروجیکٹ ری ایکٹر" کی منطق کا استعمال کرتا ہے جو رفتار اور معیار میں توازن رکھتی ہے۔
    """
    try:
        df = convert_candles_to_dataframe(candles)
        if df.empty or len(df) < 34:
            return {"status": "no-signal", "reason": f"تجزیے کے لیے ناکافی ڈیٹا ({len(df)} کینڈلز)۔"}

        # مرحلہ 1: انکولی حکمت عملی کا تجزیہ چلائیں
        analysis = await asyncio.to_thread(generate_adaptive_analysis, df, market_regime, symbol_personality)

        if analysis.get("status") != "ok":
            return analysis

        core_signal = analysis.get("signal")
        strategy_type = analysis.get("strategy_type", "Unknown")
        technical_score = analysis.get("score", 0) # تکنیکی اسکور حاصل کریں
        
        # مرحلہ 2: اضافی تصدیق کے لیے ڈیٹا حاصل کریں
        pattern_task = asyncio.to_thread(detect_patterns, df)
        news_task = get_news_analysis_for_symbol(symbol)
        
        pattern_data, news_data = await asyncio.gather(pattern_task, news_task)

        # === پروجیکٹ ری ایکٹر: نیا اعتماد کا نظام ===
        # مرحلہ 3: اعتماد کا اسکور متعین کریں
        
        # تکنیکی اسکور کی بنیاد پر بنیادی اعتماد (70% سے 90% تک)
        base_confidence = 70 + ((abs(technical_score) - 35) / 65 * 20)
        
        bonus_points = 0
        # اضافی شرط: کینڈل اسٹک پیٹرن
        pattern_type = pattern_data.get("type", "neutral")
        if (core_signal == "buy" and pattern_type == "bullish") or \
           (core_signal == "sell" and pattern_type == "bearish"):
            bonus_points += 5
        
        # اضافی شرط: کوئی اعلیٰ اثر والی خبر نہیں
        if news_data.get("impact") != "High":
            bonus_points += 5

        # حتمی اعتماد کا اسکور
        confidence = base_confidence + bonus_points
        confidence = min(99.0, confidence)

        # اگر اعتماد کا اسکور حتمی حد سے کم ہے تو مسترد کر دیں
        if confidence < strategy_settings.FINAL_CONFIDENCE_THRESHOLD:
            return {"status": "no-signal", "reason": f"اعتماد ({confidence:.2f}%) تھریشولڈ سے کم ہے۔"}

        # === پروجیکٹ ری ایکٹر: سگنل گریڈنگ اور متحرک رسک ===
        # مرحلہ 4: گریڈ اور TP/SL کو ایڈجسٹ کریں
        
        signal_grade = "B-Grade"
        if confidence >= 85:
            signal_grade = "A-Grade"

        tp = analysis.get("tp")
        sl = analysis.get("sl")
        price = analysis.get("price")
        risk = abs(price - sl)

        # B-Grade سگنل کے لیے چھوٹا اور تیز منافع
        if signal_grade == "B-Grade":
            if core_signal == "buy":
                tp = price + (risk * 1.5)
            else:
                tp = price - (risk * 1.5)
            logger.info(f"B-Grade سگنل: RR کو 1:1.5 پر ایڈجسٹ کیا گیا۔ نیا TP: {tp:.5f}")

        # مرحلہ 5: حتمی سگنل تیار کریں
        reason = generate_reason(
            core_signal, pattern_data, news_data, confidence, 
            strategy_type, market_regime, signal_grade
        )

        return {
            "status": "ok",
            "symbol": symbol,
            "signal": core_signal,
            "reason": reason,
            "confidence": round(confidence, 2),
            "timeframe": "15min",
            "price": price,
            "tp": round(tp, 5),
            "sl": round(sl, 5),
            "strategy_type": strategy_type,
            "signal_grade": signal_grade
        }

    except Exception as e:
        logger.error(f"[{symbol}] کے لیے فیوژن انجن میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        return {"status": "error", "reason": f"AI فیوژن میں ایک غیر متوقع خرابی۔"}
        
