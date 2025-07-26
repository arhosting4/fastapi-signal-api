# filename: fusion_engine.py

import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session

# مقامی امپورٹس
from strategybot import generate_core_signal, calculate_tp_sl
from patternai import detect_patterns
from riskguardian import check_risk
from sentinel import get_news_analysis_for_symbol
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from supply_demand import get_market_structure_analysis
from schemas import Candle

logger = logging.getLogger(__name__)

async def generate_final_signal(db: Session, symbol: str, candles: List[Candle], timeframe: str) -> Dict[str, Any]:
    """
    تمام AI سگنلز کو ملا کر ایک حتمی سگنل بناتا ہے۔
    یہ اب ٹائم فریم کو بھی مدنظر رکھتا ہے۔
    """
    try:
        candle_dicts = [c.model_dump() for c in candles]

        # 1. بنیادی سگنل (اب ٹائم فریم کے ساتھ)
        core_signal_data = generate_core_signal(candle_dicts, timeframe)
        core_signal = core_signal_data["signal"]

        if core_signal == "wait":
            return {"status": "no-signal", "reason": f"بنیادی حکمت عملی ({timeframe}) غیر جانبدار ہے۔"}

        # 2. اضافی تجزیہ
        pattern_data = detect_patterns(candle_dicts)
        risk_assessment = check_risk(candle_dicts)
        news_data = await get_news_analysis_for_symbol(symbol)
        market_structure = get_market_structure_analysis(candle_dicts)

        # 3. حفاظتی فلٹرز
        if risk_assessment.get("status") == "High" or news_data.get("impact") == "High":
            logger.info(f"[{symbol} - {timeframe}] سگنل کو زیادہ رسک یا خبروں کی وجہ سے بلاک کر دیا گیا۔")
            return {"status": "blocked", "reason": "زیادہ رسک یا زیادہ اثر والی خبریں۔"}

        # 4. اعتماد کا اسکور
        confidence = get_confidence(
            db, core_signal, pattern_data.get("type", "neutral"),
            risk_assessment.get("status"), news_data.get("impact"), symbol, timeframe
        )
        tier = get_tier(confidence)
        
        # 5. TP/SL کا حساب (اب ٹائم فریم کے ساتھ)
        tp_sl_data = calculate_tp_sl(candle_dicts, core_signal, timeframe)
        if not tp_sl_data:
            return {"status": "no-signal", "reason": "TP/SL کا حساب نہیں لگایا جا سکا"}
        
        tp, sl = tp_sl_data

        # 6. حتمی وجہ
        reason = generate_reason(
            core_signal, pattern_data, risk_assessment.get("status"),
            news_data.get("impact"), confidence, market_structure
        )

        return {
            "status": "ok",
            "symbol": symbol,
            "signal": core_signal,
            "pattern": pattern_data.get("pattern"),
            "risk": risk_assessment.get("status"),
            "news": news_data.get("impact"),
            "reason": reason,
            "confidence": round(confidence, 2),
            "tier": tier,
            "timeframe": timeframe, # <-- اہم: ٹائم فریم کو سگنل میں شامل کیا گیا
            "price": candle_dicts[-1]['close'],
            "tp": round(tp, 5),
            "sl": round(sl, 5),
        }

    except Exception as e:
        logger.error(f"{symbol} ({timeframe}) کے لیے فیوژن انجن ناکام: {e}", exc_info=True)
        return {"status": "error", "reason": f"{symbol} ({timeframe}) کے لیے AI فیوژن میں خرابی۔"}
        
