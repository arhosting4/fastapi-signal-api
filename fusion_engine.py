import traceback
import pandas as pd
import pandas_ta as ta

# ہمارے پروجیکٹ کے ایجنٹس
from strategybot import generate_core_signal, calculate_tp_sl
from patternai import detect_patterns
from riskguardian import check_risk
from sentinel import get_news_analysis_for_symbol
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from signal_tracker import add_active_signal
from marketstructure import analyze_market_structure
from utils import fetch_twelve_data_ohlc
# --- نیا: سپلائی اور ڈیمانڈ ایجنٹ کو امپورٹ کریں ---
from supply_demand import find_zones, analyze_price_in_zones

def get_higher_timeframe_trend(candles: list) -> str:
    # ... (یہ فنکشن ویسے ہی رہے گا) ...
    if len(candles) < 50: return "neutral"
    df = pd.DataFrame(candles)
    df['close'] = pd.to_numeric(df['close'])
    sma_fast = ta.sma(df['close'], length=20)
    sma_slow = ta.sma(df['close'], length=50)
    if sma_fast is None or sma_slow is None: return "neutral"
    if sma_fast.iloc[-1] > sma_slow.iloc[-1]: return "up"
    elif sma_fast.iloc[-1] < sma_slow.iloc[-1]: return "down"
    else: return "neutral"

async def generate_final_signal(symbol: str, candles: list, timeframe: str, should_save_active: bool = True):
    """
    یہ مرکزی AI انجن ہے۔ اب یہ سپلائی اور ڈیمانڈ زونز کا تجزیہ بھی کرتا ہے۔
    """
    try:
        # 1. بنیادی فلٹرز (پہلے کی طرح)
        news_data = get_news_analysis_for_symbol(symbol)
        if news_data["impact"] == "High":
            return {"signal": "wait", "reason": news_data['reason']}

        core_signal_data = generate_core_signal(symbol, timeframe, candles)
        core_signal = core_signal_data["signal"]
        if core_signal == "wait":
            return {"signal": "wait", "reason": "Primary indicators suggest no clear opportunity."}

        current_price = candles[-1]['close']
        structure_analysis = analyze_market_structure(core_signal, current_price, candles)
        if structure_analysis["decision"] == "block":
            return {"signal": "wait", "reason": structure_analysis['reason']}

        # --- 2. نیا اور اہم مرحلہ: سپلائی اور ڈیمانڈ کا تجزیہ ---
        zones = find_zones(candles)
        price_location = analyze_price_in_zones(current_price, zones)
        
        # اگر BUY سگنل ہے لیکن قیمت سپلائی زون میں ہے -> بلاک کریں
        if core_signal == "buy" and price_location.get("in_supply"):
            reason = f"BUY signal blocked. Price is inside a supply zone ({price_location['in_supply']['bottom']:.4f} - {price_location['in_supply']['top']:.4f})."
            print(f"S/D ANALYSIS ({symbol}): {reason}")
            return {"signal": "wait", "reason": reason}

        # اگر SELL سگنل ہے لیکن قیمت ڈیمانڈ زون میں ہے -> بلاک کریں
        if core_signal == "sell" and price_location.get("in_demand"):
            reason = f"SELL signal blocked. Price is inside a demand zone ({price_location['in_demand']['bottom']:.4f} - {price_location['in_demand']['top']:.4f})."
            print(f"S/D ANALYSIS ({symbol}): {reason}")
            return {"signal": "wait", "reason": reason}

        # 3. اضافی تصدیق (پہلے کی طرح)
        higher_timeframe_map = {"1m": "5m", "5m": "15m", "15m": "1h"}
        confirmation_tf = higher_timeframe_map.get(timeframe)
        htf_trend = "neutral"
        if confirmation_tf:
            htf_candles = await fetch_twelve_data_ohlc(symbol, confirmation_tf)
            if htf_candles: htf_trend = get_higher_timeframe_trend(htf_candles)

        if (core_signal == "buy" and htf_trend == "down") or (core_signal == "sell" and htf_trend == "up"):
            return {"signal": "wait", "reason": f"Signal blocked by opposing trend on {confirmation_tf}."}

        # 4. اعتماد کا اسکور اور حتمی نتیجہ
        pattern_data = detect_patterns(candles)
        risk_assessment = check_risk(candles)
        
        confidence = get_confidence(
            core_signal, pattern_data.get("type"), risk_assessment.get("status"), 
            news_data["impact"], symbol, timeframe
        )
        
        confidence += structure_analysis["confidence_boost"]
        if (core_signal == "buy" and htf_trend == "up") or (core_signal == "sell" and htf_trend == "down"):
            confidence += 10
        
        # --- سپلائی/ڈیمانڈ کی بنیاد پر اعتماد میں اضافہ ---
        sd_reason_part = ""
        if core_signal == "buy" and not price_location.get("in_supply"):
            # اگر قیمت کسی قریبی ڈیمانڈ زون سے نکلی ہے تو یہ ایک اچھا اشارہ ہے
            for zone in zones.get("demand", []):
                if price > zone['top'] and (price - zone['top']) < (zone['top'] - zone['bottom']) * 2:
                    confidence += 10
                    sd_reason_part = "Confirmed by recent bounce from a demand zone."
                    print(f"S/D ANALYSIS ({symbol}): +10 confidence boost from demand zone.")
                    break
        
        if core_signal == "sell" and not price_location.get("in_demand"):
            # اگر قیمت کسی قریبی سپلائی زون سے نکلی ہے تو یہ ایک اچھا اشارہ ہے
            for zone in zones.get("supply", []):
                if price < zone['bottom'] and (zone['bottom'] - price) < (zone['top'] - zone['bottom']) * 2:
                    confidence += 10
                    sd_reason_part = "Confirmed by recent rejection from a supply zone."
                    print(f"S/D ANALYSIS ({symbol}): +10 confidence boost from supply zone.")
                    break

        confidence = min(100.0, confidence)
        tier = get_tier(confidence)
        base_reason = generate_reason(core_signal, pattern_data, risk_assessment.get("status"), news_data["impact"], confidence)
        final_reason = f"{base_reason} {sd_reason_part}".strip()

        tp_sl_buy, tp_sl_sell = calculate_tp_sl(candles)
        tp, sl = (tp_sl_buy if core_signal == "buy" else tp_sl_sell) if (tp_sl_buy and tp_sl_sell) else (None, None)

        final_result = {
            "symbol": symbol, "timeframe": timeframe, "signal": core_signal, 
            "reason": final_reason, "confidence": round(confidence, 2), "tier": tier, 
            "price": current_price, "tp": tp, "sl": sl, "candles": candles
        }

        if should_save_active and final_result["signal"] in ["buy", "sell"] and tp is not None and sl is not None:
            add_active_signal(final_result)

        return final_result

    except Exception as e:
        traceback.print_exc()
        return {"signal": "wait", "reason": f"An error occurred during analysis: {e}"}
        
