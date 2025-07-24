# filename: fusion_engine.py
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session

import config
from strategybot import generate_core_signal, calculate_tp_sl
from patternai import detect_patterns
from riskguardian import check_risk, get_dynamic_atr_multiplier
from sentinel import get_news_analysis_for_symbol
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from supply_demand import get_market_structure_analysis
from schemas import Candle

logger = logging.getLogger(__name__)

async def generate_final_signal(db: Session, symbol: str, candles_data: List[Dict], timeframe: str) -> Dict[str, Any]:
    """
    تمام AI سگنلز کو فیوز کرتا ہے اور میٹا ڈیٹا کے ساتھ ایک حتمی اعلیٰ اعتماد والا سگنل واپس کرتا ہے۔
    """
    try:
        # Pydantic کے ساتھ کینڈل ڈیٹا کی توثیق کریں
        candles = [Candle(**c) for c in candles_data]
        
        # مرحلہ 1: بنیادی سگنل
        core_signal_data = generate_core_signal(candles)
        core_signal = core_signal_data["signal"]

        if core_signal == "wait":
            return {"status": "no-signal", "reason": "بنیادی حکمت عملی غیر جانبدار ہے۔"}

        # مرحلہ 2: پیٹرن، رسک، خبریں اور مارکیٹ کا ڈھانچہ
        pattern_data = detect_patterns(candles)
        risk_assessment = check_risk(candles)
        news_data = await get_news_analysis_for_symbol(symbol)
        market_structure = get_market_structure_analysis(candles)

        # مرحلہ 3: زیادہ رسک یا خبروں کو بلاک کریں
        if risk_assessment.get("status") == "High" or news_data.get("impact") == "High":
            reason = f"زیادہ رسک (ATR: {risk_assessment.get('reason')}) یا اعلیٰ اثر والی خبر ({news_data.get('reason')}) کی وجہ سے بلاک کیا گیا۔"
            logger.info(f"{symbol}: {reason}")
            return {"status": "blocked", "reason": reason}

        # مرحلہ 4: اعتماد کی منطق
        confidence = get_confidence(
            db,
            core_signal,
            pattern_data.get("type", "neutral"),
            risk_assessment.get("status"),
            news_data.get("impact"),
            symbol
        )
        tier = get_tier(confidence)
        reason = generate_reason(
            core_signal,
            pattern_data,
            risk_assessment.get("status"),
            news_data.get("impact"),
            confidence,
            market_structure
        )

        # مرحلہ 5: TP/SL منطق
        atr_multiplier = get_dynamic_atr_multiplier(risk_assessment.get("status"))
        tp_sl_data = calculate_tp_sl(candles, atr_multiplier=atr_multiplier)

        tp, sl = None, None
        if tp_sl_data:
            if core_signal == "buy":
                tp, sl = tp_sl_data[0]
            elif core_signal == "sell":
                tp, sl = tp_sl_data[1]

        last_candle = candles[-1]
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
            "timeframe": timeframe,
            "price": last_candle.close,
            "tp": round(tp, 5) if tp is not None else None,
            "sl": round(sl, 5) if sl is not None else None,
        }

    except Exception as e:
        logger.error(f"{symbol} کے لیے فیوژن انجن ناکام: {e}", exc_info=True)
        return {"status": "error", "reason": f"{symbol} کے لیے AI فیوژن میں خرابی: {e}"}
        
