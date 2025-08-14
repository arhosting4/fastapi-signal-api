import asyncio
import logging
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy.orm import Session

from strategy_scalper import run_trading_committee 
from config import strategy_settings
# reasonbot کی اب ضرورت نہیں
# from reasonbot import generate_reason
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
    یہ "ٹریڈنگ کمیٹی" کی منطق کا استعمال کرتا ہے اور ہر فیصلے کو لاگ کرتا ہے۔
    """
    try:
        df = convert_candles_to_dataframe(candles)
        if df.empty or len(df) < 34:
            return {"status": "no-signal", "reason": f"تجزیے کے لیے ناکافی ڈیٹا ({len(df)} کینڈلز)۔"}

        symbol_personality['symbol'] = symbol 
        analysis = await asyncio.to_thread(run_trading_committee, df, market_regime, symbol_personality)

        if analysis.get("status") != "ok":
            logger.info(f"透明 [{symbol}]: کمیٹی نے سگنل مسترد کر دیا۔ وجہ: {analysis.get('reason', 'نامعلوم')}")
            return analysis

        news_task = get_news_analysis_for_symbol(symbol)
        news_data = await news_task

        # ★★★ نیا، متوازن اعتماد کا فارمولا ★★★
        signal_grade = analysis.get("signal_grade", "F")
        
        # 1. گریڈ کی بنیاد پر بنیادی اعتماد
        base_confidence = {"A+": 85.0, "A": 75.0, "B": 65.0}.get(signal_grade, 50.0)

        # 2. کمیٹی کے اسکور کی بنیاد پر تھوڑا ایڈجسٹمنٹ
        # مثال: اگر اسکور 100 ہے تو 0 ایڈجسٹمنٹ، اگر 200 ہے تو +10
        score_adjustment = (abs(analysis.get('score', 0)) - 100) / 10 

        # 3. خبروں کا اثر
        news_penalty = 15 if news_data.get("impact") == "High" else 0

        confidence = base_confidence + score_adjustment - news_penalty
        confidence = min(99.0, max(40.0, confidence)) # اعتماد کو 40 اور 99 کے درمیان رکھیں

        final_check_log = (
            f"透明 [{symbol}]: حتمی جانچ: سگنل={analysis.get('signal')}, گریڈ={signal_grade}, "
            f"کمیٹی اسکور={analysis.get('score')}, حتمی اعتماد={confidence:.1f}%"
        )
        logger.info(final_check_log)

        if confidence < strategy_settings.FINAL_CONFIDENCE_THRESHOLD:
            logger.warning(f"透明 [{symbol}]: سگنل مسترد۔ وجہ: حتمی اعتماد ({confidence:.1f}%) تھریشولڈ ({strategy_settings.FINAL_CONFIDENCE_THRESHOLD}%) سے کم ہے۔")
            return {"status": "no-signal", "reason": f"اعتماد ({confidence:.2f}%) تھریشولڈ سے کم ہے۔"}

        reason = analysis.get("reason")
        logger.info(f"✅ [{symbol}]: سگنل منظور! گریڈ: {signal_grade}, اعتماد: {confidence:.1f}%")

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
        
