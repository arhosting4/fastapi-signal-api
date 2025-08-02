# filename: fusion_engine.py

import asyncio
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from sentinel import get_news_analysis_for_symbol
from riskguardian import check_risk
from strategybot import generate_technical_analysis_score, calculate_tp_sl
from patternai import get_pattern_signal
from tierbot import get_tier
from trainerai import get_confidence
from models import ActiveSignal
import database_crud as crud
from websocket_manager import manager as ws_manager
from schemas import SignalData

logger = logging.getLogger(__name__)

async def run_full_pipeline(db: Session, symbol: str, df):
    """
    مرکزی async سگنل pipeline: ہر symbol پر (hunter job سے) کال ہوتی ہے۔
    ہر analysis (news, risk, strategy, pattern) کو اکٹھا کرے، confidence + tier نکالے، اور
    اگرrequirements پوری ہوں تو DB + websocket پر سگنل publish کرے۔
    """
    # Async parallel analysis
    news_task = get_news_analysis_for_symbol(symbol)
    risk_task = asyncio.to_thread(check_risk, df)
    strategy_task = asyncio.to_thread(generate_technical_analysis_score, df)
    pattern_task = asyncio.to_thread(get_pattern_signal, df)
    news_result, risk_result, strategy_result, pattern_result = await asyncio.gather(
        news_task, risk_task, strategy_task, pattern_task
    )

    logger.info(f"FusionEngine | [{symbol}] news: {news_result} | risk: {risk_result} | strategy: {strategy_result} | pattern: {pattern_result}")

    risk_status = risk_result.get("status", "Normal")
    news_impact = news_result.get("impact", "Clear")
    technical_score = strategy_result.get("score", 0)
    reason_all = "; ".join([
        f"news: {news_result.get('reason','')}",
        f"risk: {risk_result.get('reason','')}",
        f"strategy: {strategy_result.get('reason','')}",
        f"pattern: {pattern_result.get('reason','')}",
    ])

    core_signal = "buy" if technical_score > 0 else "sell"
    pattern_signal_type = pattern_result.get("signal_type", "")

    confidence = get_confidence(
        db=db,
        core_signal=core_signal,
        technical_score=technical_score,
        pattern_signal_type=pattern_signal_type,
        risk_status=risk_status,
        news_impact=news_impact,
        symbol=symbol
    )
    tier = get_tier(confidence, risk_status)
    logger.info(f"FusionEngine [{symbol}] Final confidence: {confidence} | Tier: {tier}")

    # FIRE ONLY IF: enough confidence, no critical risk/news
    if (confidence >= 60) and not (risk_status == "Critical" or news_impact == "High"):
        tp_sl = calculate_tp_sl(df, core_signal)
        if not tp_sl:
            logger.warning(f"[{symbol}] TP/SL calculation failed; skipping signal.")
            return

        tp, sl = tp_sl
        signal_data = SignalData(
            signal_id=f"{symbol}_{df.iloc[-1]['datetime']}",
            symbol=symbol,
            timeframe="15min",
            signal_type=core_signal,
            entry_price=df['close'].iloc[-1],
            tp_price=tp,
            sl_price=sl,
            confidence=confidence,
            reason=reason_all,
            timestamp=str(df.iloc[-1]['datetime'])
        )

        # DB save — you need to implement this helper in database_crud
        if hasattr(crud, "save_signal_to_db"):
            crud.save_signal_to_db(db, signal_data)
        else:
            logger.warning("save_signal_to_db not implemented in database_crud.py")

        # Broadcast via websocket
        await ws_manager.broadcast(signal_data.model_dump())
        logger.info(f"FusionEngine | [{symbol}] Signal fired & broadcasted. Data: {signal_data.model_dump()}")
    else:
        logger.info(f"FusionEngine | [{symbol}] Signal blocked: low confidence or high risk/news. {reason_all}")
        
