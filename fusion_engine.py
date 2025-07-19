import random
import traceback
from sqlalchemy.orm import Session

from strategybot import generate_core_signal, calculate_tp_sl, get_dynamic_atr_multiplier
from patternai import detect_patterns
from riskguardian import check_risk
from sentinel import get_news_analysis_for_symbol
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from supply_demand import get_market_structure_analysis
import database_crud as crud

async def generate_final_signal(db: Session, symbol: str, candles: list, timeframe: str):
    try:
        core_signal_data = generate_core_signal(candles)
        core_signal = core_signal_data["signal"]
        
        if core_signal == "wait" and len(candles) < 34:
            return {"status": "no-signal", "signal": "wait", "reason": "Insufficient historical data."}

        pattern_data = detect_patterns(candles)
        market_structure = get_market_structure_analysis(candles)
        risk_assessment = check_risk(candles)
        news_data = get_news_analysis_for_symbol(symbol)
        
        if risk_assessment["status"] == "High" or news_data["impact"] == "High":
            reason = risk_assessment["reason"] if risk_assessment["status"] == "High" else news_data["reason"]
            return {"status": "blocked", "signal": "wait", "reason": f"BLOCKED: {reason}"}

        confidence = get_confidence(db, core_signal, pattern_data["type"], risk_assessment["status"], news_data["impact"], symbol)
        tier = get_tier(confidence)
        reason = generate_reason(core_signal, pattern_data, risk_assessment, news_data, confidence, market_structure)
        
        atr_multiplier = get_dynamic_atr_multiplier(risk_assessment["status"])
        tp_sl_data = calculate_tp_sl(candles, atr_multiplier)
        
        tp, sl = (None, None)
        if core_signal == "buy" and tp_sl_data: tp, sl = tp_sl_data[0]
        elif core_signal == "sell" and tp_sl_data: tp, sl = tp_sl_data[1]

        if not all([tp, sl]):
             return {"status": "no-signal", "signal": "wait", "reason": "Could not calculate TP/SL."}

        return {
            "status": "ok", "symbol": symbol, "signal": core_signal, "reason": reason,
            "confidence": round(confidence, 2), "tier": tier, "timeframe": timeframe,
            "price": candles[-1]['close'], "tp": round(tp, 5), "sl": round(sl, 5)
        }
    except Exception as e:
        print(f"--- CRITICAL ERROR in fusion_engine for {symbol}: {e} ---")
        traceback.print_exc()
        return {"status": "error", "reason": f"Error in AI fusion for {symbol}: {e}"}
    
