import asyncio
import logging
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy.orm import Session

# ★★★ نیا امپورٹ ★★★
from strategy_scalper import run_trading_committee 
from config import strategy_settings
from patternai import detect_patterns
from reasonbot import generate_reason
from schemas import Candle
from sentinel import get_news_analysis_for_symbol
from utils import convert_candles_to_dataframe

logger = logging.getLogger(__name__)

async def generate_final_signal(
    db: Session, 
    symbol: str, 
    candles: List[Candle], 
    market_regime: Dict,
    symbol_personality: Dict
) -> Dict[str, Any]:
    """
    ایک حتمی، قابلِ عمل سگنل تیار کرتا ہے۔
    یہ اب "ٹریڈنگ کمیٹی" کی منطق کا استعمال کرتا ہے اور ہر فیصلے کو لاگ کرتا ہے۔
    """
    try:
        df = convert_candles_to_dataframe(candles)
        if df.empty or len(df) < 34:
            return {"status": "no-signal", "reason": f"تجزیے کے لیے ناکافی ڈیٹا ({len(df)} کینڈلز)۔"}

        # مرحلہ 1: ٹریڈنگ کمیٹی کا تجزیہ چلائیں
        # ★★★ مرکزی تبدیلی یہاں ہے ★★★
        # ہم نے symbol_personality کو بھی پاس کیا ہے تاکہ لاگنگ بہتر ہو
        symbol_personality['symbol'] = symbol 
        analysis = await asyncio.to_thread(run_trading_committee, df, market_regime, symbol_personality)

        if analysis.get("status") != "ok":
            logger.info(f"透明 [{symbol}]: کمیٹی نے سگنل مسترد کر دیا۔ وجہ: {analysis.get('reason', 'نامعلوم')}")
            return analysis

        # مرحلہ 2: اضافی تصدیق کے لیے ڈیٹا حاصل کریں (یہ حصہ ویسے ہی رہے گا)
        news_task = get_news_analysis_for_symbol(symbol)
        news_data = await news_task # پیٹرن کی اب ضرورت نہیں کیونکہ کمیٹی خود زیادہ ذہین ہے

        # مرحلہ 3: اعتماد کا اسکور متعین کریں
        # ہم اب کمیٹی کے دیے گئے اسکور اور گریڈ پر زیادہ انحصار کریں گے
        base_confidence = 60.0 + (analysis.get('score', 0) / 200 * 30) # اسکور کی بنیاد پر
        
        # گریڈ کی بنیاد پر بونس
        grade_bonus = {"A+": 10, "A": 5, "B": 0}.get(analysis.get("signal_grade"), 0)
        
        # خبروں کا اثر
        news_penalty = 15 if news_data.get("impact") == "High" else 0

        confidence = base_confidence + grade_bonus - news_penalty
        confidence = min(99.0, max(40.0, confidence)) # اعتماد کو 40 اور 99 کے درمیان رکھیں

        # مرحلہ 4: حتمی منظوری سے پہلے فیصلے کو لاگ کریں
        final_check_log = (
            f"透明 [{symbol}]: حتمی جانچ: سگنل={analysis.get('signal')}, گریڈ={analysis.get('signal_grade')}, "
            f"کمیٹی اسکور={analysis.get('score')}, حتمی اعتماد={confidence:.1f}%"
        )
        logger.info(final_check_log)

        if confidence < strategy_settings.FINAL_CONFIDENCE_THRESHOLD:
            logger.warning(f"透明 [{symbol}]: سگنل مسترد۔ وجہ: حتمی اعتماد ({confidence:.1f}%) تھریشولڈ ({strategy_settings.FINAL_CONFIDENCE_THRESHOLD}%) سے کم ہے۔")
            return {"status": "no-signal", "reason": f"اعتماد ({confidence:.2f}%) تھریشولڈ سے کم ہے۔"}

        # مرحلہ 5: حتمی سگنل تیار کریں
        # ہم اب reasonbot کی بجائے کمیٹی کی دی گئی وجہ کا استعمال کریں گے
        reason = analysis.get("reason")

        logger.info(f"✅ [{symbol}]: سگنل منظور! گریڈ: {analysis.get('signal_grade')}, اعتماد: {confidence:.1f}%")

        # کمیٹی سے آنے والے تمام ڈیٹا کو واپس بھیجیں
        final_signal_data = analysis.copy()
        final_signal_data.update({
            "symbol": symbol,
            "confidence": round(confidence, 2),
            "reason": reason,
            "timeframe": "15min",
        })
        return final_signal_data

    except Exception as e:
        logger.error(f"[{symbol}] کے لیے فیوژن انجن میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        return {"status": "error", "reason": f"AI فیوژن میں ایک غیر متوقع خرابی۔"}
    
