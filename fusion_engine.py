# filename: fusion_engine.py

import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session

# مقامی امپورٹس
import strategybot as sb
from riskguardian import check_risk
from sentinel import get_news_analysis_for_symbol
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from schemas import Candle

logger = logging.getLogger(__name__)

async def generate_final_signal(db: Session, symbol: str, m15_candles: List[Candle], m5_candles: List[Candle]) -> Dict[str, Any]:
    """
    نئی ملٹی ٹائم فریم منطق کا استعمال کرتے ہوئے حتمی سگنل بناتا ہے۔
    """
    try:
        m15_candle_dicts = [c.model_dump() for c in m15_candles]
        m5_candle_dicts = [c.model_dump() for c in m5_candles]

        # 1. M15 سے بڑے رجحان کی شناخت کریں
        m15_trend = sb.get_m15_trend(m15_candle_dicts)
        if m15_trend == "Sideways":
            return {"status": "no-signal", "reason": f"[{symbol}] M15 پر کوئی واضح رجحان نہیں۔"}

        # 2. M5 پر انٹری سگنل تلاش کریں
        m5_signal_data = sb.get_m5_signal(m5_candle_dicts, m15_trend)
        core_signal = m5_signal_data.get("signal")
        if core_signal == "wait":
            return {"status": "no-signal", "reason": f"[{symbol}] M15 رجحان ({m15_trend}) کے باوجود M5 پر کوئی انٹری پوائنٹ نہیں۔"}

        # 3. رسک اور خبروں کا تجزیہ
        risk_assessment = check_risk(m5_candle_dicts) # رسک M5 پر چیک کریں
        news_data = await get_news_analysis_for_symbol(symbol)

        # 4. اعتماد کا اسکور
        confidence = get_confidence(
            m15_trend=m15_trend,
            m5_signal_data=m5_signal_data,
            risk_status=risk_assessment.get("status"),
            news_impact=news_data.get("impact"),
            symbol=symbol,
            db=db
        )
        tier = get_tier(confidence)
        
        # 5. TP/SL کا حساب
        tp_sl_data = sb.calculate_dynamic_tp_sl(m5_candle_dicts, core_signal)
        if not tp_sl_data:
            return {"status": "no-signal", "reason": "TP/SL کا حساب نہیں لگایا جا سکا"}
        tp, sl = tp_sl_data

        # 6. حتمی وجہ
        reason = generate_reason(
            m15_trend=m15_trend,
            m5_signal_data=m5_signal_data,
            risk_status=risk_assessment.get("status"),
            news_impact=news_data.get("impact"),
            confidence=confidence
        )

        return {
            "status": "ok",
            "symbol": symbol,
            "signal": core_signal,
            "risk": risk_assessment.get("status"),
            "news": news_data.get("impact"),
            "reason": reason,
            "confidence": round(confidence, 2),
            "tier": tier,
            "timeframe": "5min (Entry) on 15min (Trend)", # ٹائم فریم کو واضح کیا گیا
            "price": m5_candle_dicts[-1]['close'],
            "tp": round(tp, 5),
            "sl": round(sl, 5),
        }

    except Exception as e:
        logger.error(f"[{symbol}] کے لیے فیوژن انجن ناکام: {e}", exc_info=True)
        return {"status": "error", "reason": f"[{symbol}] کے لیے AI فیوژن میں خرابی۔"}
        
