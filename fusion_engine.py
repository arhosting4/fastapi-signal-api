import traceback
from typing import Dict, Any
from sqlalchemy.orm import Session

from strategybot import generate_core_signal, calculate_tp_sl
from patternai import detect_patterns
from riskguardian import check_risk, get_dynamic_atr_multiplier
from sentinel import get_news_analysis_for_symbol
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from market_structure import get_market_structure_analysis

async def generate_final_signal(db: Session, symbol: str, candles: list, timeframe: str) -> Dict[str, Any]:
    try:
        core_signal_data = generate_core_signal(symbol, timeframe, candles)
        core_signal = core_signal_data["signal"]
        
        if core_signal == "wait" and len(candles) < 34:
            return {"status": "no-signal", "reason": "Insufficient historical data."}

        pattern_data = detect_patterns(candles)
        risk_assessment = check_risk(candles)
        news_data = await get_news_analysis_for_symbol(symbol)
        market_structure = get_market_structure_analysis(candles)

        if risk_assessment.get("status") == "High" or news_data.get("impact") == "High":
            return {"status": "blocked", "reason": "High risk or high impact news."}

        confidence = get_confidence(db, core_signal, pattern_data.get("type"), risk_assessment.get("status"), news_data.get("impact"), symbol)
        tier = get_tier(confidence)
        reason = generate_reason(core_signal, pattern_data, risk_assessment.get("status"), news_data.get("impact"), confidence, market_structure)

        atr_multiplier = get_dynamic_atr_multiplier(risk_assessment.get("status"))
        tp_sl_data = calculate_tp_sl(candles, atr_multiplier=atr_multiplier)
        
        tp, sl = (None, None)
        if tp_sl_data:
            if core_signal == "buy": tp, sl = tp_sl_data[0]
            elif core_signal == "sell": tp, sl = tp_sl_data[1]

        return {
            "status": "ok" if core_signal != "wait" else "no-signal",
            "symbol": symbol, "signal": core_signal, "pattern": pattern_data.get("pattern"),
            "risk": risk_assessment.get("status"), "news": news_data.get("impact"), "reason": reason,
            "confidence": round(confidence, 2), "tier": tier, "timeframe": timeframe,
            "price": candles[-1]['close'] if candles else None,
            "tp": round(tp, 5) if tp is not None else None,
            "sl": round(sl, 5) if sl is not None else None,
        }
    except Exception as e:
        print(f"--- CRITICAL ERROR in fusion_engine for {symbol}: {e} ---")
        traceback.print_exc()
        return {"status": "error", "reason": f"Error in AI fusion for {symbol}: {e}"}
        
