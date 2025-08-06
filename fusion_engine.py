import asyncio
import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from config import api_settings
from patternai import detect_patterns
from reasonbot import generate_reason
from sentinel import get_news_analysis_for_symbol
from trainerai import get_confidence
from utils import convert_candles_to_dataframe, fetch_twelve_data_ohlc
from strategy_scalper import generate_scalping_analysis

logger = logging.getLogger(__name__)

async def generate_final_signal(
    db: Session, 
    symbol: str, 
    candles: List[Dict[str, Any]], 
    symbol_personality: Dict,
    market_regime: Dict
) -> Dict[str, Any]:
    """
    ایک سادہ اور موثر طریقے سے تمام تجزیاتی ماڈیولز سے حاصل کردہ معلومات کو ملا کر
    ایک حتمی، قابلِ عمل سگنل تیار کرتا ہے۔
    """
    try:
        df = convert_candles_to_dataframe(candles)
        if df.empty or len(df) < 50:
            return {"status": "no-signal", "reason": f"تجزیے کے لیے ناکافی ڈیٹا ({len(df)} کینڈلز)۔"}

        # مرحلہ 1: بنیادی حکمت عملی کا تجزیہ چلائیں
        # یہ اب خود ہی ایک حقیقت پسندانہ TP/SL کا تعین کرے گا
        analysis = generate_scalping_analysis(df, symbol_personality, market_regime)

        if analysis.get("status") != "ok":
            return analysis # اگر کوئی سگنل نہیں ہے تو واپس جائیں

        core_signal = analysis.get("signal")
        
        # مرحلہ 2: اضافی فلٹرز اور سیاق و سباق کا تجزیہ
        pattern_task = asyncio.to_thread(detect_patterns, df)
        news_task = get_news_analysis_for_symbol(symbol)
        
        pattern_data, news_data = await asyncio.gather(
            pattern_task, news_task
        )

        # مرحلہ 3: حتمی سگنل تیار کریں
        confidence = get_confidence(
            db, core_signal, analysis.get("score", 0),
            pattern_data.get("type", "neutral"),
            news_data.get("impact"), symbol, symbol_personality
        )
        
        reason = generate_reason(
            core_signal, pattern_data, news_data, confidence, 
            indicators=analysis.get("indicators", {})
        )

        return {
            "status": "ok",
            "symbol": symbol,
            "signal": core_signal,
            "pattern": pattern_data.get("pattern"),
            "news": news_data.get("impact"),
            "reason": reason,
            "confidence": round(confidence, 2),
            "timeframe": "15min",
            "price": analysis.get("price"),
            "tp": round(analysis.get("tp"), 5),
            "sl": round(analysis.get("sl"), 5),
            "component_scores": analysis.get("indicators", {}).get("component_scores", {})
        }

    except Exception as e:
        logger.error(f"[{symbol}] کے لیے فیوژن انجن میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        return {"status": "error", "reason": f"AI فیوژن میں ایک غیر متوقع خرابی۔"}
        
