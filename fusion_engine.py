import traceback
import httpx
from strategybot import generate_core_signal, calculate_tp_sl
from patternai import detect_patterns
from riskguardian import check_risk
from sentinel import check_news
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
# signal_tracker کو ابھی استعمال نہیں کر رہے، لیکن مستقبل کے لیے رکھ سکتے ہیں
# from signal_tracker import add_active_signal

async def generate_final_signal(symbol: str, candles: list, timeframe: str):
    """
    تمام AI ایجنٹس سے ڈیٹا اکٹھا کرکے ایک حتمی، جامع ٹریڈنگ سگنل تیار کرتا ہے۔
    """
    try:
        # 1. بنیادی تکنیکی تجزیہ سے سگنل حاصل کریں
        core_signal_data = generate_core_signal(symbol, timeframe, candles)
        core_signal = core_signal_data["signal"]
        
        # اگر ڈیٹا بہت کم ہے تو فوری طور پر انتظار کا سگنل دیں
        if core_signal == "wait" and len(candles) < 34:
            return {
                "signal": "wait",
                "reason": "Insufficient historical data for a reliable analysis.",
                "confidence": 30.0,
                "tier": "Tier 5 – Weak",
                "price": candles[-1]['close'] if candles else None,
                "tp": None,
                "sl": None,
                "candles": candles,
                "pattern": "Insufficient Data",
                "risk": "Unknown",
                "news": "Unknown"
            }

        # 2. کینڈل اسٹک پیٹرن کا پتہ لگائیں
        pattern_data = detect_patterns(candles)
        pattern_name = pattern_data.get("pattern", "No Specific Pattern")
        pattern_type = pattern_data.get("type", "neutral")

        # 3. مارکیٹ کے رسک کا اندازہ لگائیں
        risk_assessment = check_risk(candles)
        risk_status = risk_assessment.get("status", "Normal")
        risk_reason = risk_assessment.get("reason", "Market risk appears normal.")

        # 4. اہم خبروں کی جانچ کریں (غیر مطابقت پذیر طریقے سے)
        async with httpx.AsyncClient() as client:
            news_data = await check_news(symbol, client)
        news_impact = news_data.get("impact", "Clear")
        news_reason = news_data.get("reason", "News analysis complete.")

        # 5. اگر رسک یا خبریں بہت زیادہ ہیں تو ٹریڈنگ کو بلاک کریں
        if risk_status == "High" or news_impact == "High":
            block_reason = f"Trading Blocked: {risk_reason}" if risk_status == "High" else f"Trading Blocked: {news_reason}"
            return {
                "signal": "wait",
                "reason": block_reason,
                "confidence": 10.0,
                "tier": "Tier 5 – Weak",
                "price": candles[-1]['close'] if candles else None,
                "tp": None,
                "sl": None,
                "candles": candles,
                "pattern": pattern_name,
                "risk": risk_status,
                "news": news_impact
            }

        # 6. تمام معلومات کی بنیاد پر اعتماد کا سکور حاصل کریں
        confidence = get_confidence(core_signal, pattern_type, risk_status, news_impact, symbol)
        
        # 7. اعتماد کی بنیاد پر ٹئیر (درجہ) حاصل کریں
        tier = get_tier(confidence)
        
        # 8. سگنل کی وجہ واضح اور جامع الفاظ میں بنائیں
        reason = generate_reason(core_signal, pattern_data, risk_status, news_impact, confidence)

        # 9. ٹیک پرافٹ (TP) اور اسٹاپ لاس (SL) کا حساب لگائیں
        tp_sl_buy, tp_sl_sell = calculate_tp_sl(candles)
        tp = None
        sl = None

        if core_signal == "buy" and tp_sl_buy:
            tp, sl = tp_sl_buy
        elif core_signal == "sell" and tp_sl_sell:
            tp, sl = tp_sl_sell

        # 10. حتمی نتیجہ تیار کریں
        final_result = {
            "signal": core_signal,
            "price": candles[-1]['close'] if candles else None,
            "tp": round(tp, 5) if tp is not None else None,
            "sl": round(sl, 5) if sl is not None else None,
            "confidence": round(confidence, 2),
            "tier": tier,
            "reason": reason,
            "pattern": pattern_name,
            "risk": risk_status,
            "news": news_impact,
            "timeframe": timeframe,
            "symbol": symbol,
            "candles": candles
        }

        # اگر سگنل درست ہے تو اسے ٹریکر میں شامل کریں (مستقبل کے لیے)
        # if final_result["signal"] != "wait" and tp is not None and sl is not None:
        #     add_active_signal(final_result)

        return final_result

    except Exception as e:
        print(f"CRITICAL ERROR in fusion_engine for {symbol}: {e}")
        traceback.print_exc()
        # ایک محفوظ ایرر میسج واپس بھیجیں
        return {
            "signal": "wait",
            "reason": f"An internal AI error occurred: {e}",
            "confidence": 0.0,
            "tier": "Error",
            "price": candles[-1]['close'] if candles else None,
            "tp": None,
            "sl": None,
            "candles": candles,
            "pattern": "Error",
            "risk": "Error",
            "news": "Error"
        }
        
