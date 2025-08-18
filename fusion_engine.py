import asyncio
import logging
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy.orm import Session

from config import api_settings, strategy_settings
from patternai import detect_patterns
from reasonbot import generate_reason
from schemas import Candle
from sentinel import get_news_analysis_for_symbol
# نیا امپورٹ
from utils import convert_candles_to_dataframe, fetch_polygon_volume_data
from strategy_scalper import generate_adaptive_analysis, analyze_volume_momentum

logger = logging.getLogger(__name__)

async def generate_final_signal(
    db: Session, 
    symbol: str, 
    candles: List[Candle], 
    market_regime: Dict,
    symbol_personality: Dict
) -> Dict[str, Any]:
    try:
        df = convert_candles_to_dataframe(candles)
        if df.empty or len(df) < 34:
            return {"status": "no-signal", "reason": f"تجزیے کے لیے ناکافی ڈیٹا ({len(df)} کینڈلز)۔"}

        # --- مرحلہ 1: تمام تجزیے متوازی طور پر چلائیں ---
        
        # ★★★ نیا: حجم کا ڈیٹا الگ سے حاصل کریں ★★★
        polygon_volumes_task = fetch_polygon_volume_data([symbol], api_settings.PRIMARY_TIMEFRAME, api_settings.CANDLE_COUNT)
        
        # دیگر تجزیے
        base_strategy_task = asyncio.to_thread(generate_adaptive_analysis, df, market_regime, symbol_personality)
        pattern_task = asyncio.to_thread(detect_patterns, df)
        news_task = get_news_analysis_for_symbol(symbol)

        # تمام ٹاسک کے نتائج کا انتظار کریں
        results = await asyncio.gather(
            polygon_volumes_task, base_strategy_task, pattern_task, news_task, 
            return_exceptions=True
        )
        
        polygon_volumes, base_strategy, pattern, news = results

        # --- مرحلہ 2: اسکورنگ انجن ---
        if not isinstance(base_strategy, dict) or base_strategy.get("status") != "ok":
            reason = base_strategy.get('reason', 'بنیادی شرائط پوری نہیں ہوئیں') if isinstance(base_strategy, dict) else 'بنیادی تجزیہ ناکام'
            logger.info(f"透明 [{symbol}]: سگنل کا عمل روکا گیا۔ وجہ: {reason}")
            return {"status": "no-signal", "reason": reason}

        total_score = 0
        core_signal = base_strategy["signal"]
        log_details = []

        total_score += base_strategy.get("score", 0)
        log_details.append(f"بنیادی حکمت عملی: +{base_strategy.get('score', 0)}")

        # ★★★ نیا: حجم کے ڈیٹا کو ضم کریں اور تجزیہ کریں ★★★
        if isinstance(polygon_volumes, dict) and symbol in polygon_volumes:
            volumes_list = polygon_volumes[symbol]
            # یقینی بنائیں کہ حجم کی فہرست کی لمبائی DataFrame کے برابر ہے
            if len(volumes_list) >= len(df):
                # چونکہ Polygon کا ڈیٹا تازہ ترین سے پرانا ہے، اسے الٹا کریں
                df['volume'] = volumes_list[:len(df)][::-1]
                
                # اب قابل اعتماد حجم کے ساتھ تجزیہ کریں
                volume_analysis = analyze_volume_momentum(df)
                if volume_analysis.get("status") == "CONFIRMED":
                    if volume_analysis.get("strength") == "HIGH":
                        total_score += 25
                        log_details.append("حجم: +25 (مضبوط)")
                    else:
                        total_score += 15
                        log_details.append("حجم: +15 (کمزور)")
                elif volume_analysis.get("status") == "NOT_CONFIRMED":
                    total_score -= 10
                    log_details.append("حجم: -10 (ناکافی)")
            else:
                log_details.append("حجم: 0 (ڈیٹا کی لمبائی میں فرق)")
        else:
            log_details.append("حجم: 0 (دستیاب نہیں)")

        # پیٹرن کا اسکور
        if isinstance(pattern, dict):
            pattern_type = pattern.get("type", "neutral")
            if (core_signal == "buy" and pattern_type == "bullish") or (core_signal == "sell" and pattern_type == "bearish"):
                total_score += 15
                log_details.append(f"پیٹرن: +15 ({pattern.get('pattern')})")
            elif (core_signal == "buy" and pattern_type == "bearish") or (core_signal == "sell" and pattern_type == "bullish"):
                total_score -= 20
                log_details.append(f"پیٹرن: -20 (مخالف: {pattern.get('pattern')})")

        # خبروں کا اسکور
        if isinstance(news, dict):
            if news.get("impact") == "High":
                total_score -= 30
                log_details.append("خبریں: -30 (اعلیٰ اثر)")
            else:
                total_score += 10
                log_details.append("خبریں: +10 (صاف)")

        # --- مرحلہ 3: حتمی فیصلہ ---
        confidence = max(0, min(99, total_score))
        logger.info(f"透明 [{symbol}]: اسکورنگ مکمل۔ کل اسکور: {total_score} -> اعتماد: {confidence}%. تفصیلات: {', '.join(log_details)}")

        if confidence < strategy_settings.FINAL_CONFIDENCE_THRESHOLD:
            logger.warning(f"透明 [{symbol}]: سگنل مسترد۔ وجہ: حتمی اعتماد ({confidence}%) تھریشولڈ ({strategy_settings.FINAL_CONFIDENCE_THRESHOLD}%) سے کم ہے۔")
            return {"status": "no-signal", "reason": f"اعتماد ({confidence}%) تھریشولڈ سے کم ہے۔"}

        # --- مرحلہ 4: سگنل کی تفصیلات تیار کریں ---
        signal_grade = "B-Grade"
        if confidence >= 85:
            signal_grade = "A-Grade"

        reason = generate_reason(
            core_signal, pattern, news, confidence, 
            base_strategy["strategy_type"], market_regime, signal_grade
        )

        logger.info(f"✅ [{symbol}]: سگنل منظور! گریڈ: {signal_grade}, اعتماد: {confidence}%, حکمت عملی: {base_strategy['strategy_type']}")

        return {
            "status": "ok", "symbol": symbol, "signal": core_signal, "reason": reason,
            "confidence": round(confidence, 2), "timeframe": "15min", "price": base_strategy["price"],
            "tp": round(base_strategy["tp"], 5), "sl": round(base_strategy["sl"], 5),
            "strategy_type": base_strategy["strategy_type"], "signal_grade": signal_grade
        }

    except Exception as e:
        logger.error(f"[{symbol}] کے لیے فیوژن انجن میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        return {"status": "error", "reason": f"AI فیوژن میں ایک غیر متوقع خرابی۔"}
                
