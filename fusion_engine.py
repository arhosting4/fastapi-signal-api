# filename: fusion_engine.py

import logging
import pandas as pd
from typing import Dict, Any, List
from sqlalchemy.orm import Session

# مقامی امپورٹس
from strategybot import generate_technical_analysis_score, calculate_tp_sl
from patternai import detect_patterns
from riskguardian import check_risk
from sentinel import get_news_analysis_for_symbol
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from level_analyzer import find_market_structure
from schemas import Candle
from config import STRATEGY

logger = logging.getLogger(__name__)

SIGNAL_SCORE_THRESHOLD = STRATEGY["SIGNAL_SCORE_THRESHOLD"]

async def generate_final_signal(db: Session, symbol: str, candles: List[Candle]) -> Dict[str, Any]:
    """
    تمام تجزیاتی ماڈیولز سے حاصل کردہ معلومات کو ملا کر ایک حتمی، قابلِ عمل سگنل تیار کرتا ہے۔
    ★★★ اب یہ مرکزی طور پر ایک پانڈاز ڈیٹا فریم تیار کرتا ہے اور اسے تمام ذیلی فنکشنز کو بھیجتا ہے۔ ★★★
    """
    try:
        # مرحلہ 1: ڈیٹا فریم کو مرکزی طور پر صرف ایک بار تیار کریں
        if not candles or len(candles) < 34:
            return {"status": "no-signal", "reason": f"تجزیے کے لیے ناکافی ڈیٹا ({len(candles)} کینڈلز)۔"}

        df = pd.DataFrame([c.dict() for c in candles])
        # بنیادی کالمز کو عددی قسم میں تبدیل کریں تاکہ حساب کتاب میں غلطی نہ ہو
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # اگر کسی اہم کالم میں NaN ویلیو ہو تو اسے ہٹا دیں
        df.dropna(subset=['open', 'high', 'low', 'close'], inplace=True)
        
        if len(df) < 34:
             return {"status": "no-signal", "reason": f"تجزیے کے لیے ناکافی ڈیٹا ({len(df)} کینڈلز)۔"}

        # مرحلہ 2: تیار شدہ ڈیٹا فریم کو تمام تجزیاتی فنکشنز میں استعمال کریں
        tech_analysis = generate_technical_analysis_score(df)
        technical_score = tech_analysis["score"]
        indicators = tech_analysis.get("indicators", {})

        core_signal = "wait"
        if technical_score >= SIGNAL_SCORE_THRESHOLD:
            core_signal = "buy"
        elif technical_score <= -SIGNAL_SCORE_THRESHOLD:
            core_signal = "sell"
        
        if core_signal == "wait":
            return {"status": "no-signal", "reason": f"تکنیکی اسکور ({technical_score:.2f}) تھریشولڈ ({SIGNAL_SCORE_THRESHOLD}) سے کم ہے۔"}

        pattern_data = detect_patterns(df)
        risk_assessment = check_risk(df)
        news_data = await get_news_analysis_for_symbol(symbol)
        market_structure = find_market_structure(df) # ★★★ اسے بھی ڈیٹا فریم بھیجیں ★★★

        final_risk_status = risk_assessment.get("status", "Normal")
        if news_data.get("impact") == "High":
            final_risk_status = "Critical" if final_risk_status == "High" else "High"
        
        confidence = get_confidence(
            db, core_signal, technical_score, pattern_data.get("type", "neutral"),
            final_risk_status, news_data.get("impact"), symbol
        )
        tier = get_tier(confidence, final_risk_status)
        
        # ★★★ اب calculate_tp_sl کو بھی ڈیٹا فریم بھیجیں ★★★
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
            "timeframe": "15min",
            "price": df['close'].iloc[-1],
            "tp": round(tp, 5),
            "sl": round(sl, 5),
            "component_scores": indicators.get("component_scores", {})
        }

    except Exception as e:
        logger.error(f"{symbol} کے لیے فیوژن انجن ناکام: {e}", exc_info=True)
        return {"status": "error", "reason": f"{symbol} کے لیے AI فیوژن میں خرابی۔"}
        
