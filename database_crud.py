# filename: database_crud.py

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, NamedTuple
import logging

# مقامی امپورٹس
from models import ActiveSignal, CompletedTrade, FeedbackEntry, CachedNews

logger = logging.getLogger(__name__)

class SignalUpdateResult(NamedTuple):
    signal: ActiveSignal
    is_new: bool

def get_active_signals_count_from_db(db: Session) -> int:
    """ڈیٹا بیس سے فعال سگنلز کی کل تعداد واپس کرتا ہے۔"""
    return db.query(func.count(ActiveSignal.id)).scalar() or 0

def get_all_active_signals_from_db(db: Session) -> List[ActiveSignal]:
    """ڈیٹا بیس سے تمام فعال سگنلز کی فہرست واپس کرتا ہے۔"""
    return db.query(ActiveSignal).all()

def get_active_signal_by_symbol(db: Session, symbol: str) -> Optional[ActiveSignal]:
    """کسی مخصوص علامت کے لیے فعال سگنل واپس کرتا ہے۔"""
    return db.query(ActiveSignal).filter(ActiveSignal.symbol == symbol).first()

def add_or_update_active_signal(db: Session, signal_data: Dict[str, Any]) -> Optional[SignalUpdateResult]:
    """
    ڈیٹا بیس میں ایک نیا سگنل شامل کرتا ہے یا اگر اسی علامت کا سگنل پہلے سے موجود ہو تو اسے اپ ڈیٹ کرتا ہے۔
    """
    try:
        symbol = signal_data.get("symbol")
        if not symbol:
            logger.error("سگنل ڈیٹا میں 'symbol' غائب ہے۔")
            return None
            
        existing_signal = get_active_signal_by_symbol(db, symbol)

        if existing_signal:
            logger.info(f"موجودہ سگنل {symbol} کو اپ ڈیٹ کیا جا رہا ہے۔")
            existing_signal.signal_type = signal_data.get('signal', existing_signal.signal_type)
            existing_signal.tp_price = signal_data.get('tp', existing_signal.tp_price)
            existing_signal.sl_price = signal_data.get('sl', existing_signal.sl_price)
            existing_signal.confidence = signal_data.get('confidence', existing_signal.confidence)
            existing_signal.reason = signal_data.get('reason', existing_signal.reason)
            existing_signal.component_scores = signal_data.get('component_scores', existing_signal.component_scores)
            # ★★★ اہم تبدیلی: اپ ڈیٹ ہونے پر سگنل کو دوبارہ نیا بنا دیں ★★★
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
                is_new=True # نیا سگنل ہمیشہ نیا ہوتا ہے
            )
            db.add(new_signal)
            db.commit()
            db.refresh(new_signal)
            return SignalUpdateResult(signal=new_signal, is_new=True)

    except Exception as e:
        logger.error(f"فعال سگنل شامل/اپ ڈیٹ کرنے میں خرابی: {e}", exc_info=True)
        db.rollback()
        return None

def add_completed_trade(db: Session, signal: ActiveSignal, outcome: str, close_price: float, reason_for_closure: str) -> Optional[CompletedTrade]:
    """
    ڈیٹا بیس سیشن میں مکمل شدہ ٹریڈ کا تفصیلی ریکارڈ شامل کرتا ہے، لیکن commit نہیں کرتا۔
    """
    existing_trade = db.query(CompletedTrade).filter(CompletedTrade.signal_id == signal.signal_id).first()
    if existing_trade:
        logger.warning(f"مکمل شدہ ٹریڈ {signal.signal_id} پہلے سے موجود ہے۔ دوبارہ شامل نہیں کیا جا رہا۔")
        return existing_trade

    db_trade = CompletedTrade(
        signal_id=signal.signal_id,
        symbol=signal.symbol,
        timeframe=signal.timeframe,
        signal_type=signal.signal_type,
        entry_price=signal.entry_price,
        tp_price=signal.tp_price,
        sl_price=signal.sl_price,
        close_price=close_price,
        reason_for_closure=reason_for_closure,
        outcome=outcome,
        confidence=signal.confidence,
        reason=signal.reason,
        closed_at=datetime.utcnow()
    )
    db.add(db_trade)
    return db_trade

def close_and_archive_signal(db: Session, signal_id: str, outcome: str, close_price: float, reason_for_closure: str) -> bool:
    """
    ایک فعال سگنل کو ڈیلیٹ کرتا ہے اور اسے مکمل شدہ ٹریڈز میں شامل کرتا ہے۔
    """
    try:
        signal_to_delete = db.query(ActiveSignal).filter(ActiveSignal.signal_id == signal_id).first()
        
        if not signal_to_delete:
            logger.warning(f"بند کرنے کے لیے فعال سگنل {signal_id} نہیں ملا۔")
            return False

        logger.info(f"فعال سگنل {signal_id} کو بند اور آرکائیو کیا جا رہا ہے۔")
        
        add_completed_trade(
            db=db,
            signal=signal_to_delete,
            outcome=outcome,
            close_price=close_price,
            reason_for_closure=reason_for_closure
        )
        
        db.delete(signal_to_delete)
        db.commit()
        
        logger.info(f"سگنل {signal_id} کامیابی سے ہسٹری میں منتقل ہو گیا۔")
        return True

    except Exception as e:
        logger.error(f"فعال سگنل {signal_id} کو بند کرنے میں خرابی: {e}", exc_info=True)
        db.rollback()
        return False

def get_completed_trades(db: Session, limit: int = 100) -> List[Dict[str, Any]]:
    """سب سے حالیہ مکمل شدہ ٹریڈز واپس کرتا ہے۔"""
    trades = db.query(CompletedTrade).order_by(desc(CompletedTrade.closed_at)).limit(limit).all()
    return [trade.as_dict() for trade in trades]

def get_daily_stats(db: Session) -> Dict[str, int]:
    """آج کے TP اور SL ہٹس کی تعداد واپس کرتا ہے۔"""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    tp_hits = db.query(func.count(CompletedTrade.id)).filter(
        CompletedTrade.outcome == 'tp_hit',
        CompletedTrade.closed_at >= today_start
    ).scalar() or 0
    
    sl_hits = db.query(func.count(CompletedTrade.id)).filter(
        CompletedTrade.outcome == 'sl_hit',
        CompletedTrade.closed_at >= today_start
    ).scalar() or 0
    
    return {"tp_hits_today": tp_hits, "sl_hits_today": sl_hits}

def update_news_cache_in_db(db: Session, news_data: Dict[str, Any]) -> None:
    """موجودہ کیش شدہ خبروں کو نئے مواد سے بدل دیتا ہے۔"""
    try:
        db.query(CachedNews).delete()
        new_news = CachedNews(content=news_data, updated_at=datetime.utcnow())
        db.add(new_news)
        db.commit()
    except Exception as e:
        logger.error(f"نیوز کیش اپ ڈیٹ کرنے میں خرابی: {e}", exc_info=True)
        db.rollback()

def get_cached_news(db: Session) -> Optional[Dict[str, Any]]:
    """DB سے کیش شدہ خبریں حاصل کرتا ہے اگر دستیاب ہوں۔"""
    try:
        news = db.query(CachedNews).order_by(desc(CachedNews.updated_at)).first()
        return news.content if news else None
    except Exception as e:
        logger.error(f"کیش شدہ خبریں بازیافت کرنے میں خرابی: {e}", exc_info=True)
        return None
        
