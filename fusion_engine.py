# filename: fusion_engine.py

# ★★★ حل: گمشدہ asyncio ماڈیول کو امپورٹ کریں ★★★
import asyncio
import logging
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy.orm import Session

# مقامی امپورٹس
from config import api_settings, strategy_settings
from level_analyzer import find_market_structure
from patternai import detect_patterns
from reasonbot import generate_reason
from riskguardian import check_risk
from schemas import Candle
from sentinel import get_news_analysis_for_symbol
from strategybot import calculate_tp_sl, generate_technical_analysis_score
from tierbot import get_tier
from trainerai import get_confidence

logger = logging.getLogger(__name__)

async def generate_final_signal(db: Session, symbol: str, candles: List[Candle]) -> Dict[str, Any]:
    """
    تمام تجزیاتی ماڈیولز سے حاصل کردہ معلومات کو ملا کر ایک حتمی، قابلِ عمل سگنل تیار کرتا ہے۔
    یہ تمام تجزیاتی کاموں کو متوازی طور پر چلاتا ہے تاکہ کارکردگی کو بہتر بنایا جا سکے۔
    """
    try:
        # مرحلہ 1: ڈیٹا فریم کو مرکزی طور پر صرف ایک بار تیار کریں
        if not candles or len(candles) < 34:
            return {"status": "no-signal", "reason": f"تجزیے کے لیے ناکافی ڈیٹا ({len(candles)} کینڈلز)۔"}

        df = pd.DataFrame([c.dict() for c in candles])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=['open', 'high', 'low', 'close'], inplace=True)
        
        if len(df) < 34:
             return {"status": "no-signal", "reason": f"تجزیے کے لیے ناکافی ڈیٹا ({len(df)} کینڈلز)۔"}

        # مرحلہ 2: تمام تجزیاتی فنکشنز کو متوازی طور پر چلائیں
        # یہ کارکردگی کو بہت بہتر بناتا ہے کیونکہ یہ کام ایک دوسرے کا انتظار نہیں کرتے۔
        # asyncio.to_thread کا استعمال یقینی بناتا ہے کہ sync فنکشنز async لوپ کو بلاک نہ کریں۔
        tech_analysis_task = asyncio.to_thread(generate_technical_analysis_score, df)
        pattern_task = asyncio.to_thread(detect_patterns, df)
        risk_task = asyncio.to_thread(check_risk, df)
        news_task = get_news_analysis_for_symbol(symbol)
        market_structure_task = asyncio.to_thread(find_market_structure, df)
        
        tech_analysis, pattern_data, risk_assessment, news_data, market_structure = await asyncio.gather(
            tech_analysis_task,
            pattern_task,
            risk_task,
            news_task,
            market_structure_task
        )

        # مرحلہ 3: نتائج کی بنیاد پر بنیادی سگنل کا تعین کریں
        technical_score = tech_analysis.get("score", 0)
        indicators = tech_analysis.get("indicators", {})
        
        core_signal = "wait"
        if technical_score >= strategy_settings.SIGNAL_SCORE_THRESHOLD:
            core_signal = "buy"
        elif technical_score <= -strategy_settings.SIGNAL_SCORE_THRESHOLD:
            core_signal = "sell"
        
        if core_signal == "wait":
            return {"status": "no-signal", "reason": f"تکنیکی اسکور ({technical_score:.2f}) تھریشولڈ سے کم ہے۔"}

        # مرحلہ 4: بقیہ ڈیٹا کی بنیاد پر حتمی سگنل تیار کریں
        final_risk_status = risk_assessment.get("status", "Normal")
        if news_data.get("impact") == "High":
            final_risk_status = "Critical" if final_risk_status == "High" else "High"
        
        confidence = get_confidence(
            db, core_signal, technical_score, pattern_data.get("type", "neutral"),
            final_risk_status, news_data.get("impact"), symbol
        )
        tier = get_tier(confidence, final_risk_status)
        
        tp_sl_data = calculate_tp_sl(df, core_signal)
        if not tp_sl_data:
            return {"status": "no-signal", "reason": "بہترین TP/SL کا حساب نہیں لگایا جا سکا"}
        
        tp, sl = tp_sl_data

        reason = generate_reason(
            core_signal, pattern_data, final_risk_status,
            news_data, confidence, market_structure, indicators=indicators
        )

        return {
            "status": "ok",
            "symbol": symbol,
            "signal": core_signal,
            "pattern": pattern_data.get("pattern"),
            "risk": final_risk_status,
            "news": news_data.get("impact"),
            "reason": reason,
            "confidence": round(confidence, 2),
            "tier": tier,
            "timeframe": api_settings.PRIMARY_TIMEFRAME,
            "price": df['close'].iloc[-1],
            "tp": round(tp, 5),
            "sl": round(sl, 5),
            "component_scores": indicators.get("component_scores", {})
        }

    except Exception as e:
        logger.error(f"[{symbol}] کے لیے فیوژن انجن میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        return {"status": "error", "reason": f"AI فیوژن میں ایک غیر متوقع خرابی۔"}
