# filename: fusion_engine.py

import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session

# مقامی امپورٹس
from strategybot import generate_technical_analysis_score, calculate_tp_sl # اپ ڈیٹ شدہ فنکشن
from patternai import detect_patterns
from riskguardian import check_risk
from sentinel import get_news_analysis_for_symbol
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from supply_demand import get_market_structure_analysis
from schemas import Candle

logger = logging.getLogger(__name__)

# ★★★ فیصلہ سازی کے لیے تھریشولڈ ★★★
SIGNAL_SCORE_THRESHOLD = 40.0 # 100 میں سے 40 کا اسکور سگنل کے لیے ضروری ہے

async def generate_final_signal(db: Session, symbol: str, candles: List[Candle]) -> Dict[str, Any]:
    """
    تمام AI ماڈیولز سے حاصل کردہ معلومات کو ملا کر ایک حتمی، اعلیٰ اعتماد والا سگنل بناتا ہے۔
    """
    try:
        candle_dicts = [c.model_dump() for c in candles]

        # 1. بنیادی تکنیکی اسکور حاصل کریں
        tech_analysis = generate_technical_analysis_score(candle_dicts)
        technical_score = tech_analysis["score"]
        indicators = tech_analysis.get("indicators", {})

        # 2. اسکور کی بنیاد پر سگنل کی سمت کا تعین کریں
        core_signal = "wait"
        if technical_score >= SIGNAL_SCORE_THRESHOLD:
            core_signal = "buy"
        elif technical_score <= -SIGNAL_SCORE_THRESHOLD:
            core_signal = "sell"
        
        if core_signal == "wait":
            return {"status": "no-signal", "reason": f"تکنیکی اسکور ({technical_score:.2f}) تھریشولڈ ({SIGNAL_SCORE_THRESHOLD}) سے کم ہے۔"}

        # 3. اضافی تجزیہ (یہ ویسے ہی رہے گا)
        pattern_data = detect_patterns(candle_dicts)
        risk_assessment = check_risk(candle_dicts)
        news_data = await get_news_analysis_for_symbol(symbol)
        market_structure = get_market_structure_analysis(candle_dicts)

        # 4. رسک کا حتمی تعین
        final_risk_status = risk_assessment.get("status", "Normal")
        if news_data.get("impact") == "High":
            final_risk_status = "Critical" if final_risk_status == "High" else "High"
        
        # 5. اعتماد کا اسکور (اب یہ تکنیکی اسکور کو بھی استعمال کرے گا)
        confidence = get_confidence(
            db, core_signal, technical_score, pattern_data.get("type", "neutral"),
            final_risk_status, news_data.get("impact"), symbol
        )
        tier = get_tier(confidence, final_risk_status)
        
        # 6. TP/SL کا حساب
        tp_sl_data = calculate_tp_sl(candle_dicts, core_signal)
        if not tp_sl_data:
            return {"status": "no-signal", "reason": "TP/SL کا حساب نہیں لگایا جا سکا"}
        
        tp, sl = tp_sl_data

        # 7. حتمی وجہ
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
            "price": candle_dicts[-1]['close'],
            "tp": round(tp, 5),
            "sl": round(sl, 5),
        }

    except Exception as e:
        logger.error(f"{symbol} کے لیے فیوژن انجن ناکام: {e}", exc_info=True)
        return {"status": "error", "reason": f"{symbol} کے لیے AI فیوژن میں خرابی۔"}```

#### **3. `trainerai.py` (اپ ڈیٹ شدہ)**
*   `get_confidence` فنکشن اب `technical_score` کو بھی اپنی کیلکولیشن میں شامل کرے گا۔

```python
# filename: trainerai.py
import random
from sqlalchemy.orm import Session
import database_crud as crud

def get_confidence(
    db: Session, 
    core_signal: str, 
    technical_score: float, # ★★★ نیا پیرامیٹر ★★★
    pattern_signal_type: str, 
    risk_status: str, 
    news_impact: str, 
    symbol: str
) -> float:
    # بنیادی اعتماد اب تکنیکی اسکور پر مبنی ہے
    # اسکور 40 پر 50% اعتماد، 100 پر 80% اعتماد
    base_confidence = 50 + ( (abs(technical_score) - 40) / 60 * 30 )
    
    multiplier = 1.0

    # پیٹرن کی تصدیق
    if (core_signal == "buy" and pattern_signal_type == "bullish") or \
       (core_signal == "sell" and pattern_signal_type == "bearish"):
        multiplier *= 1.15 # 15% اضافہ
    elif pattern_signal_type != "neutral":
        multiplier *= 0.85 # 15% کمی

    # رسک منطق
    if risk_status == "Critical":
        multiplier *= 0.40
    elif risk_status == "High":
        multiplier *= 0.65
    elif risk_status == "Moderate":
        multiplier *= 0.90

    # خبروں کا اثر
    if news_impact == "High":
        multiplier *= 0.90

    # ماضی کی کارکردگی سے سیکھنا
    feedback_stats = crud.get_feedback_stats_from_db(db, symbol)
    if feedback_stats and feedback_stats["total"] > 10:
        accuracy = feedback_stats.get("accuracy", 50.0)
        accuracy_multiplier = 0.80 + (accuracy / 250) # 0.8 سے 1.2 تک
        multiplier *= accuracy_multiplier

    confidence = base_confidence * multiplier
    confidence = max(10.0, min(99.0, confidence))
    
    return round(confidence, 2)
        
