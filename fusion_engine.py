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
from utils import convert_candles_to_dataframe, fetch_twelve_data_ohlc
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
    یہ سگنل کو A-Grade اور B-Grade میں تقسیم کرتا ہے اور متحرک رسک مینجمنٹ کرتا ہے۔
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
        
        # مرحلہ 2: اضافی تصدیق کے لیے ڈیٹا حاصل کریں
        pattern_task = asyncio.to_thread(detect_patterns, df)
        news_task = get_news_analysis_for_symbol(symbol)
        
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
        
        pattern_data, news_data = await asyncio.gather(pattern_task, news_task)

        # === پروجیکٹ ویلوسیٹی: سگنل گریڈنگ سسٹم ===
        # مرحلہ 3: سگنل کا گریڈ اور اعتماد کا اسکور متعین کریں
        
        confirmations = 0
        base_score = 70 # B-Grade سگنل کا بنیادی اسکور

        # بنیادی شرط: H1 ٹرینڈ (صرف ٹرینڈ فالوونگ کے لیے)
        if strategy_type == "Trend-Following" and h1_trend_ok:
            confirmations += 1
        
        # اضافی شرط: کینڈل اسٹک پیٹرن
        pattern_type = pattern_data.get("type", "neutral")
        if (core_signal == "buy" and pattern_type == "bullish") or \
           (core_signal == "sell" and pattern_type == "bearish"):
            confirmations += 1

        # اضافی شرط: کوئی اعلیٰ اثر والی خبر نہیں
        if news_data.get("impact") != "High":
            confirmations += 1

        # گریڈ اور اعتماد کا اسکور متعین کریں
        signal_grade = "B-Grade"
        if confirmations >= 2: # کم از کم 2 اضافی تصدیقیں
            signal_grade = "A-Grade"
            base_score = 85 # A-Grade سگنل کا بنیادی اسکور

        # حتمی اعتماد کا اسکور
        confidence = base_score + (confirmations * 3) # ہر تصدیق کے لیے 3 پوائنٹس
        confidence = min(99.0, confidence)

        # اگر اعتماد کا اسکور حتمی حد سے کم ہے تو مسترد کر دیں
        if confidence < strategy_settings.FINAL_CONFIDENCE_THRESHOLD:
            return {"status": "no-signal", "reason": f"اعتماد ({confidence:.2f}%) تھریشولڈ سے کم ہے۔"}

        # === پروجیکٹ ویلوسیٹی: متحرک رسک/ریوارڈ ===
        # مرحلہ 4: گریڈ کی بنیاد پر TP/SL کو ایڈجسٹ کریں
        
        tp = analysis.get("tp")
        sl = analysis.get("sl")
        price = analysis.get("price")
        risk = abs(price - sl)

        # B-Grade سگنل کے لیے چھوٹا اور تیز منافع
        if signal_grade == "B-Grade":
            # RR کو 1:1.5 پر سیٹ کریں
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
            "signal_grade": signal_grade # ڈیبگنگ اور تجزیے کے لیے
        }

    except Exception as e:
        logger.error(f"[{symbol}] کے لیے فیوژن انجن میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        return {"status": "error", "reason": f"AI فیوژن میں ایک غیر متوقع خرابی۔"}
        
