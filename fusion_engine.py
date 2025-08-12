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
from trainerai import get_confidence_score # اب ہم ایک نیا فنکشن استعمال کریں گے
from utils import convert_candles_to_dataframe, fetch_twelve_data_ohlc

# اب ہم strategy_scalper سے مرکزی انکولی فنکشن درآمد کریں گے
from strategy_scalper import generate_adaptive_analysis

logger = logging.getLogger(__name__)

async def generate_final_signal(
    db: Session, 
    symbol: str, 
    candles: List[Candle], 
    market_regime: str, # اب ہم مارکیٹ کا نظام براہ راست حاصل کریں گے
    symbol_personality: Dict
) -> Dict[str, Any]:
    """
    تمام تجزیاتی ماڈیولز سے حاصل کردہ معلومات کو ملا کر ایک حتمی، قابلِ عمل سگنل تیار کرتا ہے۔
    یہ مارکیٹ کے نظام کے مطابق حکمت عملی کا انتخاب کرتا ہے اور متحرک رسک مینجمنٹ کرتا ہے۔
    """
    try:
        df = convert_candles_to_dataframe(candles)
        if df.empty or len(df) < 34:
            return {"status": "no-signal", "reason": f"تجزیے کے لیے ناکافی ڈیٹا ({len(df)} کینڈلز)۔"}

        # مرحلہ 1: انکولی حکمت عملی کا تجزیہ چلائیں
        # یہ فنکشن خود صحیح حکمت عملی (ٹرینڈ/ریورسل) کا انتخاب کرے گا
        analysis = await asyncio.to_thread(generate_adaptive_analysis, df, market_regime, symbol_personality)

        if analysis.get("status") != "ok":
            return analysis # اگر کوئی سگنل نہیں ہے تو واپس جائیں

        core_signal = analysis.get("signal")
        technical_score = analysis.get("score", 0)
        strategy_type = analysis.get("strategy_type", "Unknown")
        
        # مرحلہ 2: اضافی فلٹرز اور سیاق و سباق کا تجزیہ
        pattern_task = asyncio.to_thread(detect_patterns, df)
        news_task = get_news_analysis_for_symbol(symbol)
        
        # کثیر ٹائم فریم کی تصدیق (صرف ٹرینڈ فالوونگ کے لیے)
        h1_trend_ok = True
        if strategy_type == "Trend-Following":
            h1_candles = await fetch_twelve_data_ohlc(symbol, "1h", 50)
            if h1_candles:
                h1_df = convert_candles_to_dataframe(h1_candles)
                h1_ema_slow = h1_df['close'].ewm(span=50, adjust=False).mean()
                last_h1_close = h1_df['close'].iloc[-1]
                last_h1_ema = h1_ema_slow.iloc[-1]
                
                if (core_signal == "buy" and last_h1_close < last_h1_ema) or \
                   (core_signal == "sell" and last_h1_close > last_h1_ema):
                    h1_trend_ok = False
            
        if not h1_trend_ok:
            return {"status": "no-signal", "reason": "H1 رجحان کے خلاف سگنل، مسترد کر دیا گیا۔"}

        pattern_data, news_data = await asyncio.gather(
            pattern_task, news_task
        )

        # مرحلہ 3: اعتماد کا اسکور اور متحرک رسک مینجمنٹ
        confidence = get_confidence_score(
            technical_score, pattern_data.get("type", "neutral"),
            news_data.get("impact"), symbol_personality, core_signal
        )
        
        # اگر اعتماد کا اسکور حتمی حد سے کم ہے تو سگنل کو مسترد کر دیں
        if confidence < strategy_settings.FINAL_CONFIDENCE_THRESHOLD:
            return {"status": "no-signal", "reason": f"اعتماد ({confidence:.2f}%) تھریشولڈ سے کم ہے۔"}

        # مرحلہ 4: حتمی سگنل تیار کریں
        reason = generate_reason(
            core_signal, pattern_data, news_data, confidence, 
            strategy_type, market_regime
        )

        return {
            "status": "ok",
            "symbol": symbol,
            "signal": core_signal,
            "pattern": pattern_data.get("pattern"),
            "news": news_data.get("impact"),
            "reason": reason,
            "confidence": round(confidence, 2),
            "timeframe": "15min", # ہم فی الحال 15 منٹ پر توجہ مرکوز کر رہے ہیں
            "price": analysis.get("price"),
            "tp": round(analysis.get("tp"), 5),
            "sl": round(analysis.get("sl"), 5),
            "strategy_type": strategy_type
        }

    except Exception as e:
        logger.error(f"[{symbol}] کے لیے فیوژن انجن میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        return {"status": "error", "reason": f"AI فیوژن میں ایک غیر متوقع خرابی۔"}
            
