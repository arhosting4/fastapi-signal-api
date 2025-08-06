# filename: strategies/strategy_scalper.py

import logging
from typing import Dict, Any, Optional, Tuple
import pandas as pd

# مقامی امپورٹس
from strategies.base_strategy import BaseStrategy
from level_analyzer import find_optimal_tp_sl, find_market_structure
from patternai import detect_patterns
from reasonbot import generate_reason
from trainerai import get_confidence
from config import api_settings, strategy_settings

# تکنیکی تجزیہ کے فنکشنز
from technicals.indicators import calculate_rsi, calculate_stoch, calculate_supertrend, calculate_ema
from technicals.score_calculator import get_technical_score

logger = logging.getLogger(__name__)

class ScalperStrategy(BaseStrategy):
    """
    اسکیلپنگ کے لیے ایک حکمت عملی جو کم ٹائم فریم پر تیز رفتار حرکتوں کو پکڑنے پر توجہ مرکوز کرتی ہے۔
    یہ متحرک پیرامیٹرز کا استعمال کرتی ہے۔
    """
    name = "Scalper"

    def analyze(self, db_session, symbol: str, m15_df: pd.DataFrame, h1_df: pd.DataFrame, market_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        متحرک مارکیٹ پیرامیٹرز کی بنیاد پر تجزیہ کرتا ہے۔
        """
        if len(m15_df) < 34 or len(h1_df) < 20:
            return self.result("no-signal", "تجزیے کے لیے ناکافی ڈیٹا۔")

        # 1. تکنیکی تجزیہ (15 منٹ کے ڈیٹا پر)
        tech_analysis = get_technical_score(m15_df)
        technical_score = tech_analysis.get("score", 0)
        
        core_signal = "wait"
        if technical_score >= strategy_settings.SIGNAL_SCORE_THRESHOLD:
            core_signal = "buy"
        elif technical_score <= -strategy_settings.SIGNAL_SCORE_THRESHOLD:
            core_signal = "sell"
        
        if core_signal == "wait":
            return self.result("no-signal", f"تکنیکی اسکور ({technical_score:.2f}) تھریشولڈ سے کم ہے۔")

        # 2. بڑے ٹائم فریم (1 گھنٹہ) کی تصدیق
        h1_structure = find_market_structure(h1_df)
        h1_trend = h1_structure.get("trend", "غیر متعین")

        if (core_signal == "buy" and h1_trend == "نیچے کا رجحان") or \
           (core_signal == "sell" and h1_trend == "اوپر کا رجحان"):
            return self.result("no-signal", f"H1 رجحان ({h1_trend}) سگنل کی سمت کے خلاف ہے۔")

        # 3. متحرک پیرامیٹرز کے ساتھ TP/SL کا حساب
        # ★★★ اہم تبدیلی: متحرک پیرامیٹرز کو پاس کیا جا رہا ہے ★★★
        tp_sl_data = find_optimal_tp_sl(m15_df, core_signal, market_params)
        if not tp_sl_data:
            return self.result("no-signal", "بہترین TP/SL کا حساب نہیں لگایا جا سکا (متحرک شرائط سخت ہو سکتی ہیں)۔")
        
        tp, sl = tp_sl_data

        # 4. بقیہ تجزیہ
        pattern_data = detect_patterns(m15_df)
        
        confidence = get_confidence(
            db_session, core_signal, technical_score, pattern_data.get("type", "neutral"),
            market_params.get("risk_level", "Medium"), "Clear", symbol
        )
        
        reason = generate_reason(
            core_signal, pattern_data, market_params.get("risk_level", "Medium"),
            {"impact": "Clear"}, confidence, h1_structure, indicators=tech_analysis.get("indicators", {})
        )

        return {
            "status": "ok",
            "symbol": symbol,
            "signal": core_signal,
            "confidence": round(confidence, 2),
            "reason": reason,
            "timeframe": "15min",
            "price": m15_df['close'].iloc[-1],
            "tp": round(tp, 5),
            "sl": round(sl, 5),
            "component_scores": tech_analysis.get("indicators", {}).get("component_scores", {})
            }
        
