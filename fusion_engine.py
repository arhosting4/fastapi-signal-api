# filename: fusion_engine.py

import logging
import pandas as pd
from typing import Dict, Any, List
from sqlalchemy.orm import Session

# 🧠 مقامی تجزیاتی ماڈیولز
from strategybot import generate_technical_analysis_score, calculate_tp_sl
from patternai import detect_patterns
from riskguardian import check_risk
from sentinel import get_news_analysis_for_symbol
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from level_analyzer import find_market_structure
from schemas import Candle
from config import STRATEGY

logger = logging.getLogger(__name__)

SIGNAL_SCORE_THRESHOLD = STRATEGY["SIGNAL_SCORE_THRESHOLD"]
FINAL_CONFIDENCE_THRESHOLD = STRATEGY["FINAL_CONFIDENCE_THRESHOLD"]

# =====================================================================================
async def generate_final_signal(db: Session, symbol: str, candles: List[Candle]) -> Dict[str, Any]:
    """
    تمام تجزیاتی ماڈیولز سے حاصل کردہ معلومات کو ملا کر ایک حتمی، قابلِ عمل سگنل تیار کرتا ہے۔
    ★★★ یہ مرکزی hub ہے جو تمام ماڈیولز سے data لے کر فیصلہ کرتا ہے ★★★
    """
    try:
        # 🔹 Step 1: Candles validate کریں
        if not candles or len(candles) < 34:
            return {"status": "no-signal", "reason": f"تجزیے کے لیے ناکافی ڈیٹا ({len(candles)} کینڈلز)"}

        # 🔹 Step 2: Candle DataFrame بنائیں
        df = pd.DataFrame([c.dict() for c in candles])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(inplace=True)

        current_price = df['close'].iloc[-1]

        # 🔹 Step 3: تکنیکی اسکور حاصل کریں
        tech_score = generate_technical_analysis_score(df)

        if tech_score < SIGNAL_SCORE_THRESHOLD:
            return {"status": "no-signal", "reason": f"اسکور کم ہے: {tech_score:.2f}"}

        # 🔹 Step 4: confidence ماڈل سے اعتماد حاصل کریں
        confidence = get_confidence(df)

        if confidence < FINAL_CONFIDENCE_THRESHOLD:
            return {"status": "no-signal", "reason": f"اعتماد کم ہے: {confidence:.2f}%"}

        # 🔹 Step 5: پیٹرن تجزیہ
        pattern_info = detect_patterns(df)

        # 🔹 Step 6: خبروں کا تجزیہ
        news_impact = get_news_analysis_for_symbol(db, symbol)

        # 🔹 Step 7: مارکیٹ اسٹرکچر تجزیہ
        structure = find_market_structure(df)

        # 🔹 Step 8: TP/SL کیلکولیٹ کریں
        levels = calculate_tp_sl(df)
        tp, sl = levels.get("tp"), levels.get("sl")

        if not tp or not sl:
            return {"status": "no-signal", "reason": "مناسب TP/SL نہ ملا"}

        # 🔹 Step 9: رسک چیک
        risk_check = check_risk(current_price, sl)
        if not risk_check["allowed"]:
            return {"status": "no-signal", "reason": risk_check["reason"]}

        # 🔹 Step 10: سگنل Tier نکالیں
        tier = get_tier(tech_score, confidence)

        # 🔹 Step 11: Reason Generator
        reason = generate_reason(
            symbol=symbol,
            tech_score=tech_score,
            confidence=confidence,
            pattern=pattern_info.get("pattern", ""),
            news=news_impact,
            structure=structure,
            tp=tp,
            sl=sl
        )

        # 🔹 Step 12: سگنل تیار کریں
        return {
            "status": "signal",
            "symbol": symbol,
            "score": tech_score,
            "confidence": confidence,
            "pattern": pattern_info,
            "news": news_impact,
            "structure": structure,
            "tp": tp,
            "sl": sl,
            "tier": tier,
            "reason": reason
        }

    except Exception as e:
        logger.error(f"❌ سگنل تیار کرنے میں خرابی: {e}", exc_info=True)
        return {"status": "error", "reason": "اندرونی خرابی"}
