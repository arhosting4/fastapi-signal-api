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
    یہ "پروجیکٹ ری ایکٹر" کی منطق کا استعمال کرتا ہے اور ہر فیصلے کو لاگ کرتا ہے۔
    """
    try:
        df = convert_candles_to_dataframe(candles)
        if df.empty or len(df) < 34:
            # یہ پہلے سے ہی ایک واضح وجہ ہے، لاگ کی ضرورت نہیں
            return {"status": "no-signal", "reason": f"تجزیے کے لیے ناکافی ڈیٹا ({len(df)} کینڈلز)۔"}

        # مرحلہ 1: انکولی حکمت عملی کا تجزیہ چلائیں
        analysis = await asyncio.to_thread(generate_adaptive_analysis, df, market_regime, symbol_personality)

        if analysis.get("status") != "ok":
            # === پروجیکٹ ٹرانسپیرنسی لاگ ===
            # strategy_scalper سے مسترد ہونے کی وجہ کو لاگ کریں
            logger.info(f"透明 [{symbol}]: بنیادی تجزیہ مسترد۔ وجہ: {analysis.get('reason', 'نامعلوم')}")
            return analysis

        core_signal = analysis.get("signal")
        strategy_type = analysis.get("strategy_type", "Unknown")
        technical_score = analysis.get("score", 0)
        
        # مرحلہ 2: اضافی تصدیق کے لیے ڈیٹا حاصل کریں
        pattern_task = asyncio.to_thread(detect_patterns, df)
        news_task = get_news_analysis_for_symbol(symbol)
        
        pattern_data, news_data = await asyncio.gather(pattern_task, news_task)

        # مرحلہ 3: اعتماد کا اسکور متعین کریں
        base_confidence = 70 + ((abs(technical_score) - 35) / 65 * 20)
        
        bonus_points = 0
        pattern_type = pattern_data.get("type", "neutral")
        has_pattern_confirmation = (core_signal == "buy" and pattern_type == "bullish") or \
                                   (core_signal == "sell" and pattern_type == "bearish")
        
        has_clear_news = news_data.get("impact") != "High"

        if has_pattern_confirmation:
            bonus_points += 5
        
        if has_clear_news:
            bonus_points += 5

        confidence = base_confidence + bonus_points
        confidence = min(99.0, confidence)

        # === پروجیکٹ ٹرانسپیرنسی لاگ ===
        # مرحلہ 4: حتمی منظوری سے پہلے فیصلے کو لاگ کریں
        final_check_log = (
            f"透明 [{symbol}]: حتمی جانچ: سگنل={core_signal}, ٹیک اسکور={technical_score:.1f}, "
            f"بنیادی اعتماد={base_confidence:.1f}, پیٹرن بونس={'ہاں' if has_pattern_confirmation else 'نہیں'}, "
            f"خبریں صاف={'ہاں' if has_clear_news else 'نہیں'}, حتمی اعتماد={confidence:.1f}%"
        )
        logger.info(final_check_log)

        if confidence < strategy_settings.FINAL_CONFIDENCE_THRESHOLD:
            # === پروجیکٹ ٹرانسپیرنسی لاگ ===
            # مسترد ہونے کی حتمی وجہ کو لاگ کریں
            logger.warning(f"透明 [{symbol}]: سگنل مسترد۔ وجہ: اعتماد ({confidence:.1f}%) تھریشولڈ ({strategy_settings.FINAL_CONFIDENCE_THRESHOLD}%) سے کم ہے۔")
            return {"status": "no-signal", "reason": f"اعتماد ({confidence:.2f}%) تھریشولڈ سے کم ہے۔"}

        # مرحلہ 5: گریڈ اور TP/SL کو ایڈجسٹ کریں
        signal_grade = "B-Grade"
        if confidence >= 85:
            signal_grade = "A-Grade"

        tp = analysis.get("tp")
        sl = analysis.get("sl")
        price = analysis.get("price")
        risk = abs(price - sl)

        if signal_grade == "B-Grade":
            if core_signal == "buy":
                tp = price + (risk * 1.5)
            else:
                tp = price - (risk * 1.5)
            logger.info(f"透明 [{symbol}]: B-Grade سگنل: RR کو 1:1.5 پر ایڈجسٹ کیا گیا۔ نیا TP: {tp:.5f}")

        # مرحلہ 6: حتمی سگنل تیار کریں
        reason = generate_reason(
            core_signal, pattern_data, news_data, confidence, 
            strategy_type, market_regime, signal_grade
        )

        # === پروجیکٹ ٹرانسپیرنسی لاگ ===
        # منظور شدہ سگنل کی حتمی تفصیلات لاگ کریں
        logger.info(f"✅ [{symbol}]: سگنل منظور! گریڈ: {signal_grade}, اعتماد: {confidence:.1f}%, حکمت عملی: {strategy_type}")

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
        
