# filename: database_crud.py
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from models import CompletedTrade, FeedbackEntry, CachedNews

logger = logging.getLogger(__name__)

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

def add_completed_trade(db: Session, signal_data: Dict[str, Any], outcome: str) -> Optional[CompletedTrade]:
    """ڈیٹا بیس میں مکمل شدہ ٹریڈ کا ریکارڈ شامل کرتا ہے۔"""
    try:
        required_keys = ['signal_id', 'symbol', 'timeframe', 'signal', 'price', 'tp', 'sl']
        if not all(key in signal_data for key in required_keys):
            logger.warning(f"مکمل ٹریڈ شامل کرنے کے لیے سگنل ڈیٹا میں مطلوبہ کلیدیں غائب ہیں: {signal_data}")
            return None

        db_trade = CompletedTrade(
            signal_id=signal_data['signal_id'],
            symbol=signal_data['symbol'],
            timeframe=signal_data['timeframe'],
            signal_type=signal_data['signal'],
            entry_price=signal_data['price'],
            tp_price=signal_data['tp'],
            sl_price=signal_data['sl'],
            outcome=outcome,
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

def get_completed_trades(db: Session, limit: int = 100) -> List[Dict[str, Any]]:
    """سب سے حالیہ مکمل شدہ ٹریڈز واپس کرتا ہے۔"""
    trades = db.query(CompletedTrade).order_by(desc(CompletedTrade.closed_at)).limit(limit).all()
    return [trade.as_dict() for trade in trades]

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
        
