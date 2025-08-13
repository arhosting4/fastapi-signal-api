# filename: database_crud.py

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, NamedTuple

from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# مقامی امپورٹس
from models import ActiveSignal, CompletedTrade, CachedNews
from schemas import DailyStatsResponse

logger = logging.getLogger(__name__)

class SignalUpdateResult(NamedTuple):
    signal: ActiveSignal
    is_new: bool

def get_all_active_signals_from_db(db: Session) -> List[ActiveSignal]:
    try:
        return db.query(ActiveSignal).all()
    except SQLAlchemyError as e:
        logger.error(f"تمام فعال سگنلز حاصل کرنے میں ڈیٹا بیس کی خرابی: {e}", exc_info=True)
        return []

def get_active_signal_by_symbol(db: Session, symbol: str) -> Optional[ActiveSignal]:
    try:
        return db.query(ActiveSignal).filter(ActiveSignal.symbol == symbol).first()
    except SQLAlchemyError as e:
        logger.error(f"علامت '{symbol}' کے لیے فعال سگنل حاصل کرنے میں خرابی: {e}", exc_info=True)
        return None

def add_or_update_active_signal(db: Session, signal_data: Dict[str, Any]) -> Optional[SignalUpdateResult]:
    symbol = signal_data.get("symbol")
    if not symbol:
        logger.error("سگنل ڈیٹا میں 'symbol' غائب ہے۔ سگنل شامل نہیں کیا جا سکتا۔")
        return None
        
    try:
        existing_signal = get_active_signal_by_symbol(db, symbol)

        if existing_signal:
            logger.info(f"موجودہ سگنل {symbol} کو اپ ڈیٹ کیا جا رہا ہے۔")
            existing_signal.signal_type = signal_data.get('signal', existing_signal.signal_type)
            existing_signal.tp_price = signal_data.get('tp', existing_signal.tp_price)
            existing_signal.sl_price = signal_data.get('sl', existing_signal.sl_price)
            existing_signal.confidence = signal_data.get('confidence', existing_signal.confidence)
            existing_signal.reason = signal_data.get('reason', existing_signal.reason)
            existing_signal.component_scores = signal_data.get('component_scores', existing_signal.component_scores)
            existing_signal.is_new = True
            
            db.commit()
            db.refresh(existing_signal)
            return SignalUpdateResult(signal=existing_signal, is_new=False)
        else:
            logger.info(f"نیا سگنل {symbol} بنایا جا رہا ہے۔")
            signal_id = f"{symbol.replace('/', '')}_{signal_data.get('timeframe', '15min')}_{int(datetime.utcnow().timestamp())}"
            
            new_signal = ActiveSignal(
                signal_id=signal_id,
                symbol=symbol,
                timeframe=signal_data.get('timeframe'),
                signal_type=signal_data.get('signal'),
                entry_price=signal_data.get('price'),
                tp_price=signal_data.get('tp'),
                sl_price=signal_data.get('sl'),
                confidence=signal_data.get('confidence'),
                reason=signal_data.get('reason'),
                component_scores=signal_data.get('component_scores'),
                is_new=True
            )
            db.add(new_signal)
            db.commit()
            db.refresh(new_signal)
            return SignalUpdateResult(signal=new_signal, is_new=True)

    except IntegrityError as e:
        logger.error(f"ڈیٹا بیس میں سالمیت کی خلاف ورزی: {e}", exc_info=True)
        db.rollback()
        return None
    except SQLAlchemyError as e:
        logger.error(f"فعال سگنل شامل/اپ ڈیٹ کرنے میں ڈیٹا بیس کی خرابی: {e}", exc_info=True)
        db.rollback()
        return None

def close_and_archive_signal(db: Session, signal_id: str, outcome: str, close_price: float, reason_for_closure: str) -> bool:
    signal_to_delete = db.query(ActiveSignal).filter(ActiveSignal.signal_id == signal_id).first()
    
    if not signal_to_delete:
        logger.warning(f"بند کرنے کے لیے فعال سگنل {signal_id} نہیں ملا۔")
        return False

    logger.info(f"فعال سگنل {signal_id} کو بند اور آرکائیو کیا جا رہا ہے۔ نتیجہ: {outcome}")
    
    try:
        completed_trade = CompletedTrade(
            signal_id=signal_to_delete.signal_id,
            symbol=signal_to_delete.symbol,
            timeframe=signal_to_delete.timeframe,
            signal_type=signal_to_delete.signal_type,
            entry_price=signal_to_delete.entry_price,
            tp_price=signal_to_delete.tp_price,
            sl_price=signal_to_delete.sl_price,
            close_price=close_price,
            reason_for_closure=reason_for_closure,
            outcome=outcome,
            confidence=signal_to_delete.confidence,
            reason=signal_to_delete.reason,
            # ★★★ خرابی کا حل یہاں ہے ★★★
            created_at=signal_to_delete.created_at, # یہ لائن یقینی بناتی ہے کہ صحیح ویلیو پاس ہو
            closed_at=datetime.utcnow()
        )
        db.add(completed_trade)
        
        db.delete(signal_to_delete)
        
        db.commit()
        logger.info(f"سگنل {signal_id} کامیابی سے ہسٹری میں منتقل ہو گیا۔")
        return True

    except SQLAlchemyError as e:
        logger.error(f"فعال سگنل {signal_id} کو بند کرنے میں ڈیٹا بیس کی خرابی: {e}", exc_info=True)
        db.rollback()
        return False

def get_completed_trades(db: Session, limit: int = 100) -> List[Dict[str, Any]]:
    try:
        trades = db.query(CompletedTrade).order_by(desc(CompletedTrade.closed_at)).limit(limit).all()
        return [trade.as_dict() for trade in trades]
    except SQLAlchemyError as e:
        logger.error(f"مکمل شدہ ٹریڈز حاصل کرنے میں خرابی: {e}", exc_info=True)
        return []

def get_daily_stats(db: Session) -> DailyStatsResponse:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    try:
        tp_hits = db.query(func.count(CompletedTrade.id)).filter(
            CompletedTrade.outcome == 'tp_hit',
            CompletedTrade.closed_at >= today_start
        ).scalar() or 0
        
        sl_hits = db.query(func.count(CompletedTrade.id)).filter(
            CompletedTrade.outcome == 'sl_hit',
            CompletedTrade.closed_at >= today_start
        ).scalar() or 0
        
        live_signals = db.query(func.count(ActiveSignal.id)).scalar() or 0
        
        total_today = tp_hits + sl_hits
        win_rate = (tp_hits / total_today * 100) if total_today > 0 else 0
        
        return DailyStatsResponse(
            tp_hits_today=tp_hits,
            sl_hits_today=sl_hits,
            live_signals=live_signals,
            win_rate_today=round(win_rate, 2)
        )
    except SQLAlchemyError as e:
        logger.error(f"روزانہ کے اعداد و شمار حاصل کرنے میں خرابی: {e}", exc_info=True)
        return DailyStatsResponse(tp_hits_today=0, sl_hits_today=0, live_signals=0, win_rate_today=0)

def update_news_cache_in_db(db: Session, news_data: Dict[str, Any]) -> None:
    try:
        db.query(CachedNews).delete()
        new_news = CachedNews(content=news_data, updated_at=datetime.utcnow())
        db.add(new_news)
        db.commit()
    except SQLAlchemyError as e:
        logger.error(f"نیوز کیش اپ ڈیٹ کرنے میں خرابی: {e}", exc_info=True)
        db.rollback()

def get_cached_news(db: Session) -> Optional[Dict[str, Any]]:
    try:
        news = db.query(CachedNews).order_by(desc(CachedNews.updated_at)).first()
        return news.content if news else None
    except SQLAlchemyError as e:
        logger.error(f"کیش شدہ خبریں بازیافت کرنے میں خرابی: {e}", exc_info=True)
        return None

def get_recent_sl_hits(db: Session, minutes_ago: int) -> List[CompletedTrade]:
    try:
        time_filter = datetime.utcnow() - timedelta(minutes=minutes_ago)
        return db.query(CompletedTrade).filter(
            CompletedTrade.outcome == 'sl_hit',
            CompletedTrade.closed_at >= time_filter
        ).all()
    except SQLAlchemyError as e:
        logger.error(f"حالیہ SL ہٹس حاصل کرنے میں خرابی: {e}", exc_info=True)
        return []
            
