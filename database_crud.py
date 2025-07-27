# filename: database_crud.py

from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from models import CompletedTrade, FeedbackEntry, CachedNews, ActiveSignal

logger = logging.getLogger(__name__)

# --- ActiveSignal سے متعلق فنکشنز ---

def add_active_signal_to_db(db: Session, signal_data: Dict[str, Any]) -> Optional[ActiveSignal]:
    """ایک فعال سگنل کو ڈیٹا بیس میں شامل کرتا ہے۔"""
    try:
        db_signal = ActiveSignal(
            signal_id=signal_data['signal_id'],
            symbol=signal_data['symbol'],
            timeframe=signal_data['timeframe'],
            signal_type=signal_data['signal'],
            entry_price=signal_data['price'],
            tp_price=signal_data['tp'],
            sl_price=signal_data['sl'],
            confidence=signal_data.get('confidence'),
            reason=signal_data.get('reason')
        )
        db.add(db_signal)
        db.commit()
        db.refresh(db_signal)
        return db_signal
    except Exception as e:
        logger.error(f"فعال سگنل شامل کرنے میں خرابی: {e}", exc_info=True)
        db.rollback()
        return None

def get_all_active_signals_from_db(db: Session) -> List[ActiveSignal]:
    """ڈیٹا بیس سے تمام فعال سگنلز حاصل کرتا ہے۔"""
    return db.query(ActiveSignal).all()

# ★★★ نیا فنکشن ★★★
def get_active_signal_by_symbol(db: Session, symbol: str) -> Optional[ActiveSignal]:
    """کسی مخصوص علامت کے لیے فعال سگنل حاصل کرتا ہے۔"""
    return db.query(ActiveSignal).filter(ActiveSignal.symbol == symbol).first()

def get_active_signals_count_from_db(db: Session) -> int:
    """ڈیٹا بیس میں فعال سگنلز کی تعداد واپس کرتا ہے۔"""
    return db.query(func.count(ActiveSignal.id)).scalar() or 0

# ★★★ نیا فنکشن ★★★
def update_active_signal_confidence(db: Session, signal_id: str, new_confidence: float, new_reason: str) -> Optional[ActiveSignal]:
    """کسی فعال سگنل کے اعتماد اور وجہ کو اپ ڈیٹ کرتا ہے۔"""
    try:
        signal = db.query(ActiveSignal).filter(ActiveSignal.signal_id == signal_id).first()
        if signal:
            signal.confidence = new_confidence
            signal.reason = new_reason
            db.commit()
            db.refresh(signal)
            return signal
        return None
    except Exception as e:
        logger.error(f"فعال سگنل {signal_id} کو اپ ڈیٹ کرنے میں خرابی: {e}", exc_info=True)
        db.rollback()
        return None

def remove_active_signal_from_db(db: Session, signal_id: str) -> bool:
    """ڈیٹا بیس سے ایک فعال سگنل کو ہٹاتا ہے۔"""
    try:
        signal = db.query(ActiveSignal).filter(ActiveSignal.signal_id == signal_id).first()
        if signal:
            db.delete(signal)
            db.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"فعال سگنل {signal_id} کو ہٹانے میں خرابی: {e}", exc_info=True)
        db.rollback()
        return False

# --- CompletedTrade سے متعلق فنکشنز ---

def add_completed_trade(db: Session, signal_data: ActiveSignal, outcome: str) -> Optional[CompletedTrade]:
    """ڈیٹا بیس میں مکمل شدہ ٹریڈ کا ریکارڈ شامل کرتا ہے۔"""
    try:
        db_trade = CompletedTrade(
            signal_id=signal_data.signal_id,
            symbol=signal_data.symbol,
            timeframe=signal_data.timeframe,
            signal_type=signal_data.signal_type,
            entry_price=signal_data.entry_price,
            tp_price=signal_data.tp_price,
            sl_price=signal_data.sl_price,
            outcome=outcome,
            confidence=signal_data.confidence,
            reason=signal_data.reason,
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

def get_completed_trades(db: Session, limit: int = 100) -> List[Dict[str, Any]]:
    """سب سے حالیہ مکمل شدہ ٹریڈز واپس کرتا ہے۔"""
    trades = db.query(CompletedTrade).order_by(desc(CompletedTrade.closed_at)).limit(limit).all()
    return [trade.as_dict() for trade in trades]

# --- دیگر فنکشنز ---

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
    return {"total": total, "accuracy": round(accuracy, 2), "correct": correct_count, "incorrect": incorrect_count}

def add_feedback_entry(db: Session, symbol: str, timeframe: str, feedback: str) -> Optional[FeedbackEntry]:
    """دی گئی علامت اور ٹائم فریم کے لیے DB میں فیڈ بیک اندراج شامل کرتا ہے۔"""
    try:
        entry = FeedbackEntry(symbol=symbol, timeframe=timeframe, feedback=feedback, created_at=datetime.utcnow())
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    except Exception as e:
        logger.error(f"فیڈ بیک اندراج شامل کرنے میں خرابی: {e}", exc_info=True)
        db.rollback()
        return None

def update_news_cache(db: Session, news_data: Dict[str, Any]) -> None:
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
