# filename: fusion_engine.py

import logging
from typing import Dict, Any, List

import pandas as pd
from sqlalchemy.orm import Session

# مقامی امپورٹس
from strategybot import generate_technical_analysis_score, calculate_tp_sl
from patternai import detect_patterns
from riskguardian import check_risk
from sentinel import get_news_analysis_for_symbol
from reasonbot import generate_reason
from trainerai import get_confidence
from tierbot import get_tier
from level_analyzer import find_market_structure
from schemas import Candle
# مرکزی کنفیگریشن ماڈیول سے سیٹنگز درآمد کریں
from config import strategy_settings, trading_settings

logger = logging.getLogger(__name__)

# --- کنفیگریشن سے مستقل اقدار ---
SIGNAL_SCORE_THRESHOLD = strategy_settings.SIGNAL_SCORE_THRESHOLD

def _prepare_dataframe(candles: List[Candle]) -> pd.DataFrame:
    """
    کینڈلز کی فہرست سے ایک صاف اور تجزیے کے لیے تیار پانڈاز ڈیٹا فریم بناتا ہے۔
    """
    if not candles or len(candles) < 34:
        raise ValueError(f"تجزیے کے لیے ناکافی ڈیٹا ({len(candles) if candles else 0} کینڈلز)۔")

    df = pd.DataFrame([c.dict() for c in candles])
    
    # بنیادی کالمز کو عددی قسم میں تبدیل کریں اور غلطیوں کو NaN کے طور پر سیٹ کریں
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # اگر کسی اہم کالم میں NaN ویلیو ہو تو اسے ہٹا دیں
    df.dropna(subset=['open', 'high', 'low', 'close'], inplace=True)
    
    if len(df) < 34:
        raise ValueError(f"ڈیٹا صاف کرنے کے بعد ناکافی ڈیٹا ({len(df)} کینڈلز)۔")
        
    return df

async def generate_final_signal(db: Session, symbol: str, candles: List[Candle]) -> Dict[str, Any]:
    """
    تمام تجزیاتی ماڈیولز سے حاصل کردہ معلومات کو ملا کر ایک حتمی، قابلِ عمل سگنل تیار کرتا ہے۔
    """
    try:
        # مرحلہ 1: ڈیٹا فریم کو مرکزی طور پر تیار اور صاف کریں
        df = _prepare_dataframe(candles)

        # مرحلہ 2: بنیادی تکنیکی تجزیہ کریں
        tech_analysis = generate_technical_analysis_score(df)
        technical_score = tech_analysis.get("score", 0)
        indicators = tech_analysis.get("indicators", {})

        # مرحلہ 3: بنیادی سگنل کی سمت کا تعین کریں
        core_signal = "wait"
        if technical_score >= SIGNAL_SCORE_THRESHOLD:
            core_signal = "buy"
        elif technical_score <= -SIGNAL_SCORE_THRESHOLD:
            core_signal = "sell"
        
        if core_signal == "wait":
            return {"status": "no-signal", "reason": f"تکنیکی اسکور ({technical_score:.2f}) تھریشولڈ ({SIGNAL_SCORE_THRESHOLD}) سے کم ہے۔"}

        # مرحلہ 4: تمام اضافی تجزیاتی ماڈیولز کو متوازی طور پر چلائیں
        pattern_data, risk_assessment, news_data, market_structure, tp_sl_data = await asyncio.gather(
            asyncio.to_thread(detect_patterns, df),
            asyncio.to_thread(check_risk, df),
            get_news_analysis_for_symbol(symbol),
            asyncio.to_thread(find_market_structure, df),
            asyncio.to_thread(calculate_tp_sl, df, core_signal),
            return_exceptions=True
        )

        # انفرادی ماڈیول کی ناکامیوں کو ہینڈل کریں
        if isinstance(pattern_data, Exception):
            logger.error(f"[{symbol}] پیٹرن کا پتہ لگانے میں ناکام: {pattern_data}")
            pattern_data = {"pattern": "N/A", "type": "neutral"}
        if isinstance(risk_assessment, Exception):
            logger.error(f"[{symbol}] رسک کی تشخیص میں ناکام: {risk_assessment}")
            risk_assessment = {"status": "Normal"}
        if isinstance(news_data, Exception):
            logger.error(f"[{symbol}] خبروں کے تجزیے میں ناکام: {news_data}")
            news_data = {"impact": "Clear"}
        if isinstance(market_structure, Exception):
            logger.error(f"[{symbol}] مارکیٹ کی ساخت کے تجزیے میں ناکام: {market_structure}")
            market_structure = {"trend": "غیر متعین"}
        if isinstance(tp_sl_data, Exception) or not tp_sl_data:
            logger.warning(f"[{symbol}] TP/SL کا حساب نہیں لگایا جا سکا: {tp_sl_data}")
            return {"status": "no-signal", "reason": "بہترین TP/SL کا حساب نہیں لگایا جا سکا"}

        # مرحلہ 5: حتمی پیرامیٹرز کا حساب لگائیں
        final_risk_status = risk_assessment.get("status", "Normal")
        if news_data.get("impact") == "High":
            final_risk_status = "Critical" if final_risk_status == "High" else "High"
        
        confidence = get_confidence(
            db, core_signal, technical_score, pattern_data.get("type", "neutral"),
            final_risk_status, news_data.get("impact"), symbol
        )
        tier = get_tier(confidence, final_risk_status)
        
        reason = generate_reason(
            core_signal, pattern_data, final_risk_status,
            news_data, confidence, market_structure, indicators=indicators
        )

        return {
            "status": "ok",
            "symbol": symbol,
            "signal": core_signal,
            "timeframe": trading_settings.PRIMARY_TIMEFRAME,
            "price": df['close'].iloc[-1],
            "tp": round(tp_sl_data[0], 5),
            "sl": round(tp_sl_data[1], 5),
            "confidence": round(confidence, 2),
            "tier": tier,
            "reason": reason,
            "component_scores": indicators.get("component_scores", {}),
            # اضافی معلومات
            "pattern": pattern_data.get("pattern"),
            "risk": final_risk_status,
            "news": news_data.get("impact"),
        }

    except ValueError as e:
        # _prepare_dataframe سے آنے والی خرابی
        return {"status": "no-signal", "reason": str(e)}
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے فیوژن انجن میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        return {"status": "error", "reason": f"AI فیوژن میں ایک غیر متوقع خرابی۔"}
