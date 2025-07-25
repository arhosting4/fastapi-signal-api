# filename: fusion_engine.py

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

import strategybot as sb
from riskguardian import check_risk
from sentinel import get_news_analysis_for_symbol
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from schemas import Candle

logger = logging.getLogger(__name__)

# ★★★ نیا، ہلکا پھلکا فنکشن ★★★
def check_m15_opportunity(symbol: str, m15_candles: List[Candle]) -> Optional[str]:
    """
    صرف یہ چیک کرتا ہے کہ آیا M15 پر کوئی واضح رجحان (موقع) ہے۔
    یہ ایک مکمل تجزیہ نہیں ہے اور API کالز بچانے کے لیے ہے۔
    """
    try:
        m15_candle_dicts = [c.model_dump() for c in m15_candles]
        m15_trend = sb.get_m15_trend(m15_candle_dicts)
        
        if m15_trend in ["Uptrend", "Downtrend"]:
            logger.info(f"[{symbol}] M15 پر موقع ملا: {m15_trend}")
            return m15_trend
            
    except Exception as e:
        logger.error(f"[{symbol}] M15 موقع کی جانچ میں خرابی: {e}")
    
    return None

# مکمل تجزیے کا فنکشن ویسے ہی رہے گا
async def generate_final_signal(db: Session, symbol: str, m15_trend: str, m5_candles: List[Candle]) -> Dict[str, Any]:
    """
    ایک امیدوار جوڑے کے لیے مکمل حتمی سگنل بناتا ہے۔
    نوٹ: اب یہ m15_candles کی بجائے براہ راست m15_trend لیتا ہے۔
    """
    try:
        m5_candle_dicts = [c.model_dump() for c in m5_candles]

        m5_signal_data = sb.get_m5_signal(m5_candle_dicts, m15_trend)
        core_signal = m5_signal_data.get("signal")
        if core_signal == "wait":
            return {"status": "no-signal", "reason": f"[{symbol}] M15 رجحان ({m15_trend}) کے باوجود M5 پر کوئی انٹری پوائنٹ نہیں۔"}

        risk_assessment = check_risk(m5_candle_dicts)
        news_data = await get_news_analysis_for_symbol(symbol)

        confidence = get_confidence(
            db=db, m15_trend=m15_trend, m5_signal_data=m5_signal_data,
            risk_status=risk_assessment.get("status"), news_impact=news_data.get("impact"), symbol=symbol
        )
        
        tp_sl_data = sb.calculate_dynamic_tp_sl(m5_candle_dicts, core_signal)
        if not tp_sl_data:
            return {"status": "no-signal", "reason": "TP/SL کا حساب نہیں لگایا جا سکا"}
        tp, sl = tp_sl_data

        reason = generate_reason(
            m15_trend=m15_trend, m5_signal_data=m5_signal_data,
            risk_status=risk_assessment.get("status"), news_impact=news_data.get("impact"), confidence=confidence
        )

        return {
            "status": "ok", "symbol": symbol, "signal": core_signal,
            "risk": risk_assessment.get("status"), "news": news_data.get("impact"),
            "reason": reason, "confidence": round(confidence, 2), "tier": get_tier(confidence),
            "timeframe": "5min (Entry) on 15min (Trend)", "price": m5_candle_dicts[-1]['close'],
            "tp": round(tp, 5), "sl": round(sl, 5),
        }

    except Exception as e:
        logger.error(f"[{symbol}] کے لیے فیوژن انجن ناکام: {e}", exc_info=True)
        return {"status": "error", "reason": f"[{symbol}] کے لیے AI فیوژن میں خرابی۔"}
        
