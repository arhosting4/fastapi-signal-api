# filename: database_crud.py

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from datetime import datetime
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
    یہ فنکشن اب AI کی یادداشت (component_scores) کو بھی محفوظ کرتا ہے۔
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
            db.commit()
            db.refresh(existing_signal)
            return SignalUpdateResult(signal=existing_signal, is_new=False)
        else:
            logger.info(f"نیا سگنل {symbol} بنایا جا رہا ہے۔")
            signal_id = f"{symbol}_{signal_data.get('timeframe', '15min')}_{datetime.utcnow().timestamp()}"
            
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
                component_scores=signal_data.get('component_scores')
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
    ڈیٹا بیس میں مکمل شدہ ٹریڈ کا تفصیلی ریکارڈ شامل کرتا ہے۔
    """
    try:
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
        db.commit()
        db.refresh(db_trade)
        return db_trade
    except Exception as e:
        logger.error(f"مکمل ٹریڈ شامل کرنے میں خرابی: {e}", exc_info=True)
        db.rollback()
        return None

# ★★★ مکمل طور پر نیا اور ذہین ڈیلیٹ فنکشن ★★★
def delete_active_signal(db: Session, signal_id: str, current_price: Optional[float] = None) -> bool:
    """
    ایک فعال سگنل کو ڈیلیٹ کرتا ہے اور اسے 'manual_close' کے طور پر مکمل شدہ ٹریڈز میں شامل کرتا ہے۔
    """
    try:
        signal_to_delete = db.query(ActiveSignal).filter(ActiveSignal.signal_id == signal_id).first()
        if signal_to_delete:
            logger.info(f"فعال سگنل {signal_id} کو دستی طور پر بند کیا جا رہا ہے۔")
            
            # اگر موجودہ قیمت فراہم کی گئی ہے تو اسے استعمال کریں، ورنہ انٹری قیمت استعمال کریں
            close_price = current_price if current_price is not None else signal_to_delete.entry_price
            
            # اسے 'manual_close' کے طور پر مکمل شدہ ٹریڈ میں شامل کریں
            add_completed_trade(
                db=db,
                signal=signal_to_delete,
                outcome="manual_close",
                close_price=close_price,
                reason_for_closure="Manually closed by admin"
            )
            
            # اب فعال سگنل کو ڈیلیٹ کریں
            db.delete(signal_to_delete)
            db.commit()
            logger.info(f"سگنل {signal_id} کامیابی سے ہسٹری میں منتقل ہو گیا۔")
            return True
        return False
    except Exception as e:
        logger.error(f"فعال سگنل {signal_id} کو ڈیلیٹ کرنے میں خرابی: {e}", exc_info=True)
        db.rollback()
        return False

def get_completed_trades(db: Session, limit: int = 100) -> List[Dict[str, Any]]:
    """سب سے حالیہ مکمل شدہ ٹریڈز واپس کرتا ہے۔"""
    trades = db.query(CompletedTrade).order_by(desc(CompletedTrade.closed_at)).limit(limit).all()
    return [trade.as_dict() for trade in trades]

def add_feedback_entry(db: Session, symbol: str, timeframe: str, feedback: str) -> Optional[FeedbackEntry]:
    """دی گئی علامت اور ٹائم فریم کے لیے DB میں فیڈ بیک اندراج شامل کرتا ہے۔"""
    try:
        entry = FeedbackEntry(
            symbol=symbol,
            timeframe=timeframe,
            feedback=feedback,
            created_at=datetime.utcnow()
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    except Exception as e:
        logger.error(f"فیڈ بیک اندراج شامل کرنے میں خرابی: {e}", exc_info=True)
        db.rollback()
        return None

def get_feedback_stats_from_db(db: Session, symbol: str) -> Dict[str, Any]:
    """کسی علامت کے لیے فیڈ بیک کے اعداد و شمار کا حساب لگاتا ہے۔"""
    correct_count = db.query(func.count(FeedbackEntry.id)).filter(
        FeedbackEntry.symbol == symbol, FeedbackEntry.feedback == 'correct'
    ).scalar() or 0

    incorrect_count = db.query(func.count(FeedbackEntry.id)).filter(
        FeedbackEntry.symbol == symbol, FeedbackEntry.feedback == 'incorrect'
    ).scalar() or 0

    total = correct_count + incorrect_count
    accuracy = (correct_count / total) * 100 if total > 0 else 50.0

    return {
        "total": total,
        "accuracy": round(accuracy, 2),
        "correct": correct_count,
        "incorrect": incorrect_count
    }

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
        
