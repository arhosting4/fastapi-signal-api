import asyncio
import logging
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy.orm import Session

from config import api_settings, strategy_settings
from level_analyzer import find_market_structure
from patternai import detect_patterns
from reasonbot import generate_reason
from schemas import Candle
from sentinel import get_news_analysis_for_symbol
from trainerai import get_confidence
from utils import convert_candles_to_dataframe, fetch_twelve_data_ohlc

# مرکزی حکمت عملی کا ماڈیول درآمد کریں
from strategy_scalper import generate_scalping_analysis

logger = logging.getLogger(__name__)

async def generate_final_signal(
    db: Session, 
    symbol: str, 
    candles: List[Candle], 
    market_regime: Dict,
    symbol_personality: Dict
) -> Dict[str, Any]:
    """
    تمام تجزیاتی ماڈیولز سے حاصل کردہ معلومات کو ملا کر ایک حتمی، قابلِ عمل سگنل تیار کرتا ہے۔
    یہ اب ایک واحد، انکولی اسکیلپنگ حکمت عملی پر کام کرتا ہے۔
    """
    try:
        df = convert_candles_to_dataframe(candles)
        if df.empty or len(df) < 34:
            return {"status": "no-signal", "reason": f"تجزیے کے لیے ناکافی ڈیٹا ({len(df)} کینڈلز)۔"}

        # مرحلہ 1: بنیادی حکمت عملی کا تجزیہ چلائیں
        # اب یہ ہمیشہ اسکیلپنگ تجزیہ ہی چلائے گا
        analysis = await asyncio.to_thread(generate_scalping_analysis, df, symbol_personality, market_regime)

        if analysis.get("status") != "ok":
            return analysis # اگر کوئی سگنل نہیں ہے تو واپس جائیں

        core_signal = analysis.get("signal")
        technical_score = analysis.get("score", 0)
        
        # مرحلہ 2: اضافی فلٹرز اور سیاق و سباق کا تجزیہ
        pattern_task = asyncio.to_thread(detect_patterns, df)
        news_task = get_news_analysis_for_symbol(symbol)
        market_structure_task = asyncio.to_thread(find_market_structure, df)
        
        # کثیر ٹائم فریم کی تصدیق
        h1_candles = await fetch_twelve_data_ohlc(symbol, "1h", 50)
        h1_trend_ok = True
        if h1_candles:
            h1_df = convert_candles_to_dataframe(h1_candles)
            if not h1_df.empty:
                h1_ema_slow = h1_df['close'].ewm(span=50, adjust=False).mean()
                last_h1_close = h1_df['close'].iloc[-1]
                last_h1_ema = h1_ema_slow.iloc[-1]
                
                if (core_signal == "buy" and last_h1_close < last_h1_ema) or \
                   (core_signal == "sell" and last_h1_close > last_h1_ema):
                    h1_trend_ok = False
        
        if not h1_trend_ok:
            return {"status": "no-signal", "reason": "H1 رجحان کے خلاف سگنل، مسترد کر دیا گیا۔"}

        pattern_data, news_data, market_structure = await asyncio.gather(
            pattern_task, news_task, market_structure_task
        )

        # مرحلہ 3: حتمی سگنل تیار کریں
        confidence = get_confidence(
            db, core_signal, technical_score, pattern_data.get("type", "neutral"),
            news_data.get("impact"), symbol, symbol_personality
        )
        
        reason = generate_reason(
            core_signal, pattern_data, news_data.get("impact"), news_data, confidence, 
            market_structure, indicators=analysis.get("indicators", {})
        )

        return {
            "status": "ok",
            "symbol": symbol,
            "signal": core_signal,
            "pattern": pattern_data.get("pattern"),
            "news": news_data.get("impact"),
            "reason": reason,
            "confidence": round(confidence, 2),
            "timeframe": "15min", # ٹائم فریم اب ہمیشہ 15 منٹ ہے
            "price": analysis.get("price"),
            "tp": round(analysis.get("tp"), 5),
            "sl": round(analysis.get("sl"), 5),
            "component_scores": analysis.get("indicators", {}).get("component_scores", {})
        }

    except Exception as e:
        logger.error(f"[{symbol}] کے لیے فیوژن انجن میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        return {"status": "error", "reason": f"AI فیوژن میں ایک غیر متوقع خرابی۔"}
        
