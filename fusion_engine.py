# filename: fusion_engine.py

import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from strategybot import generate_core_signal, calculate_tp_sl
from patternai import detect_patterns
from riskguardian import check_risk, get_dynamic_atr_multiplier
from sentinel import get_news_analysis_for_symbol
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from supply_demand import get_market_structure_analysis

logger = logging.getLogger(__name__)

async def generate_final_signal(db: Session, symbol: str, candles: list, timeframe: str) -> Dict[str, Any]:
    """
    Fuse all AI signals and return a final high-confidence signal with metadata.
    """
    try:
        # Step 1: Base signal
        core_signal_data = generate_core_signal(symbol, timeframe, candles)
        core_signal = core_signal_data["signal"]

        # Not enough data
        if core_signal == "wait" and len(candles) < 34:
            logger.info(f"{symbol}: Skipped - Not enough candles.")
            return {"status": "no-signal", "reason": "Insufficient historical data."}

        # Step 2: Pattern, Risk, News
        pattern_data = detect_patterns(candles)
        risk_assessment = check_risk(candles)
        news_data = await get_news_analysis_for_symbol(symbol)
        market_structure = get_market_structure_analysis(candles)

        # Step 3: Block high risk or news
        if risk_assessment.get("status") == "High" or news_data.get("impact") == "High":
            logger.info(f"{symbol}: Blocked due to high risk/news.")
            return {"status": "blocked", "reason": "High risk or high impact news."}

        # Step 4: Confidence logic
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

        # Step 5: TP/SL logic
        atr_multiplier = get_dynamic_atr_multiplier(risk_assessment.get("status"))
        tp_sl_data = calculate_tp_sl(candles, atr_multiplier=atr_multiplier)

        tp, sl = None, None
        if tp_sl_data:
            if core_signal == "buy":
                tp, sl = tp_sl_data[0]
            elif core_signal == "sell":
                tp, sl = tp_sl_data[1]

        return {
            "status": "ok" if core_signal != "wait" else "no-signal",
            "symbol": symbol,
            "signal": core_signal,
            "pattern": pattern_data.get("pattern"),
            "risk": risk_assessment.get("status"),
            "news": news_data.get("impact"),
            "reason": reason,
            "confidence": round(confidence, 2),
            "tier": tier,
            "timeframe": timeframe,
            "price": candles[-1]['close'] if candles else None,
            "tp": round(tp, 5) if tp is not None else None,
            "sl": round(sl, 5) if sl is not None else None,
        }

    except Exception as e:
        logger.error(f"Fusion engine failed for {symbol}: {e}", exc_info=True)
        return {"status": "error", "reason": f"Error in AI fusion for {symbol}: {e}"}
