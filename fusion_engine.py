from strategybot import generate_core_signal, calculate_tp_sl
from patternai import detect_patterns
from riskguardian import check_risk
from sentinel import check_news
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from signal_tracker import add_active_signal
import traceback
import httpx

async def generate_final_signal(symbol: str, candles: list, timeframe: str):
    try:
        # --- اہم تبدیلی: یہاں سے closes کی لسٹ بنانا ہٹا دیں ---
        # closes = [float(c["close"]) for c in candles] # <-- اس لائن کو ہٹا دیں

        # --- اہم تبدیلی: generate_core_signal کو پوری candles کی لسٹ بھیجیں ---
        core_signal_data = generate_core_signal(symbol, timeframe, candles) # <-- یہاں candles بھیجیں
        core_signal = core_signal_data["signal"]
        
        if core_signal == "wait" and len(candles) < 34:
            return {
                "status": "no-signal", "symbol": symbol, "signal": "wait",
                "pattern": "Insufficient Data", "risk": "Normal", "news": "Clear",
                "reason": "Insufficient historical data for a reliable signal.",
                "confidence": 50.0, "tier": "Tier 5 – Weak", "timeframe": timeframe,
                "price": candles[-1]['close'] if candles else None, "tp": None, "sl": None, "candles": candles
            }

        pattern_data = detect_patterns(candles)
        pattern_name = pattern_data.get("pattern", "No Specific Pattern")
        pattern_type = pattern_data.get("type", "neutral")

        risk_assessment = check_risk(candles)
        risk_status = risk_assessment.get("status", "Normal")
        risk_reason = risk_assessment.get("reason", "Market risk appears normal.")

        async with httpx.AsyncClient() as client:
            news_data = await check_news(symbol, client)
        news_impact = news_data["impact"]
        news_reason = news_data["reason"]

        if risk_status == "High" or news_impact == "High":
            block_reason = risk_reason if risk_status == "High" else news_reason
            return {
                "status": "blocked", "symbol": symbol, "signal": "wait",
                "pattern": pattern_name, "risk": risk_status, "news": news_impact,
                "reason": f"Trading BLOCKED: {block_reason}", "confidence": 0.0,
                "tier": "Tier 5 – Weak", "timeframe": timeframe,
                "price": candles[-1]['close'] if candles else None, "tp": None, "sl": None, "candles": candles
            }

        confidence = get_confidence(core_signal, pattern_type, risk_status, news_impact, symbol)
        tier = get_tier(confidence)
        reason = generate_reason(core_signal, pattern_data, risk_status, news_impact, confidence)

        tp_sl_buy, tp_sl_sell = calculate_tp_sl(candles)
        tp = None
        sl = None

        if core_signal == "buy" and tp_sl_buy:
            tp, sl = tp_sl_buy
        elif core_signal == "sell" and tp_sl_sell:
            tp, sl = tp_sl_sell

        final_result = {
            "status": "ok" if core_signal != "wait" else "no-signal",
            "symbol": symbol, "signal": core_signal, "pattern": pattern_name,
            "risk": risk_status, "news": news_impact, "reason": reason,
            "confidence": round(confidence, 2), "tier": tier, "timeframe": timeframe,
            "price": candles[-1]['close'] if candles else None,
            "tp": round(tp, 5) if tp is not None else None,
            "sl": round(sl, 5) if sl is not None else None,
            "candles": candles
        }

        if final_result["status"] == "ok" and tp is not None and sl is not None:
            add_active_signal(symbol, final_result)

        return final_result

    except Exception as e:
        print(f"CRITICAL ERROR in fusion_engine for {symbol}: {e}")
        traceback.print_exc()
        raise Exception(f"Error in AI fusion for {symbol}: {e}")
        
