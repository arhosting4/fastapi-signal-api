import asyncio
import logging
from typing import Any, Dict

import pandas as pd
from sqlalchemy.orm import Session

from config import strategy_settings
from patternai import detect_patterns
from reasonbot import generate_reason
from sentinel import get_news_analysis_for_symbol
from strategy_scalper import generate_adaptive_analysis, analyze_volume_momentum

logger = logging.getLogger(__name__)

async def generate_final_signal(
    db: Session, 
    symbol: str, 
    # ★★★ تبدیلی: اب ہم براہ راست DataFrame لیتے ہیں ★★★
    df: pd.DataFrame, 
    market_regime: Dict,
    symbol_personality: Dict
) -> Dict[str, Any]:
    """
    ایک حتمی، قابلِ عمل سگنل تیار کرتا ہے جو ایک ہی، قابل اعتماد ڈیٹا سورس پر مبنی ایک جامع اسکورنگ ماڈل کا استعمال کرتا ہے۔
    """
    try:
        if df.empty or len(df) < 34:
            return {"status": "no-signal", "reason": f"تجزیے کے لیے ناکافی ڈیٹا ({len(df)} کینڈلز)۔"}

        # --- مرحلہ 1: تمام تجزیے متوازی طور پر چلائیں ---
        tasks = {
            "base_strategy": asyncio.to_thread(generate_adaptive_analysis, df, market_regime, symbol_personality),
            "volume": asyncio.to_thread(analyze_volume_momentum, df),
            "pattern": asyncio.to_thread(detect_patterns, df),
            "news": get_news_analysis_for_symbol(symbol),
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        analysis_results = dict(zip(tasks.keys(), results))

        # --- مرحلہ 2: اسکورنگ انجن ---
        base_strategy = analysis_results.get("base_strategy")
        if not isinstance(base_strategy, dict) or base_strategy.get("status") != "ok":
            reason = base_strategy.get('reason', 'بنیادی شرائط پوری نہیں ہوئیں') if isinstance(base_strategy, dict) else 'بنیادی تجزیہ ناکام'
            logger.info(f"透明 [{symbol}]: سگنل کا عمل روکا گیا۔ وجہ: {reason}")
            return {"status": "no-signal", "reason": reason}

        total_score = 0
        core_signal = base_strategy["signal"]
        log_details = []

        # 2.1: بنیادی حکمت عملی کا اسکور
        total_score += base_strategy.get("score", 0)
        log_details.append(f"بنیادی حکمت عملی: +{base_strategy.get('score', 0)}")

        # 2.2: حجم کا اسکور
        volume = analysis_results.get("volume", {})
        if isinstance(volume, dict):
            if volume.get("status") == "CONFIRMED":
                if volume.get("strength") == "HIGH":
                    total_score += 25
                    log_details.append("حجم: +25 (مضبوط)")
                else: # LOW strength
                    total_score += 15
                    log_details.append("حجم: +15 (کمزور)")
            elif volume.get("status") == "NOT_CONFIRMED":
                total_score -= 10
                log_details.append("حجم: -10 (ناکافی)")

        # 2.3: پیٹرن کا اسکور
        pattern = analysis_results.get("pattern", {})
        if isinstance(pattern, dict):
            pattern_type = pattern.get("type", "neutral")
            if (core_signal == "buy" and pattern_type == "bullish") or \
               (core_signal == "sell" and pattern_type == "bearish"):
                total_score += 15
                log_details.append(f"پیٹرن: +15 ({pattern.get('pattern')})")
            elif (core_signal == "buy" and pattern_type == "bearish") or \
                 (core_signal == "sell" and pattern_type == "bullish"):
                total_score -= 20
                log_details.append(f"پیٹرن: -20 (مخالف: {pattern.get('pattern')})")

        # 2.4: خبروں کا اسکور
        news = analysis_results.get("news", {})
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
            "confidence": round(confidence, 2), "timeframe": api_settings.PRIMARY_TIMEFRAME, "price": base_strategy["price"],
            "tp": round(base_strategy["tp"], 5), "sl": round(base_strategy["sl"], 5),
            "strategy_type": base_strategy["strategy_type"], "signal_grade": signal_grade
        }

    except Exception as e:
        logger.error(f"[{symbol}] کے لیے فیوژن انجن میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        return {"status": "error", "reason": f"AI فیوژن میں ایک غیر متوقع خرابی۔"}
        
