# filename: database_crud.py

from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from src.database.models import CompletedTrade, FeedbackEntry, CachedNews

logger = logging.getLogger(__name__)

def get_feedback_stats_from_db(db: Session, symbol: str) -> Dict[str, Any]:
    """Calculate feedback statistics for a symbol."""
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
    """Add a completed trade record to the database."""
    try:
        required_keys = ['signal_id', 'symbol', 'timeframe', 'signal', 'price', 'tp', 'sl']
        if not all(key in signal_data for key in required_keys):
            logger.warning("Missing keys in signal data.")
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
        logger.error(f"Error adding completed trade: {e}")
        return None

def add_feedback_entry(db: Session, symbol: str, timeframe: str, feedback: str) -> Optional[FeedbackEntry]:
    """Add feedback entry to DB for given symbol and timeframe."""
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
        logger.error(f"Error adding feedback entry: {e}")
        return None

def get_completed_trades(db: Session, limit: int = 100) -> List[Dict[str, Any]]:
    """Return most recent completed trades."""
    trades = db.query(CompletedTrade).order_by(desc(CompletedTrade.closed_at)).limit(limit).all()
    return [trade.as_dict() for trade in trades]

def update_news_cache(db: Session, news_data: Dict[str, Any]) -> None:
    """Replace existing cached news with new content."""
    try:
        db.query(CachedNews).delete()
        new_news = CachedNews(content=news_data, updated_at=datetime.utcnow())
        db.add(new_news)
        db.commit()
    except Exception as e:
        logger.error(f"Error updating news cache: {e}")

def get_cached_news(db: Session) -> Optional[Dict[str, Any]]:
    """Fetch cached news from DB if available."""
    try:
        news = db.query(CachedNews).order_by(desc(CachedNews.updated_at)).first()
        return news.content if news else None
    except Exception as e:
        logger.error(f"Error retrieving cached news: {e}")
        return None
      # ... (other crud functions) ...

def add_active_signal(db: Session, signal_data: Dict[str, Any]):
    """Adds a new active signal to the database."""
    db_signal = ActiveSignal(
        signal_id=signal_data['signal_id'],
        symbol=signal_data['symbol'],
        timeframe=signal_data['timeframe'],
        signal_type=signal_data['signal'],
        entry_price=signal_data['entry_price'],
        tp_price=signal_data['tp_price'],
        sl_price=signal_data['sl_price'],
        confidence=signal_data['confidence'],
        reason=signal_data.get('reason', '')
    )
    db.add(db_signal)
    db.commit()
    db.refresh(db_signal)
    return db_signal

def get_all_active_signals(db: Session) -> List[ActiveSignal]:
    """Retrieves all active signals from the database."""
    return db.query(ActiveSignal).all()

def remove_active_signal(db: Session, signal_id: str):
    """Removes an active signal from the database by its signal_id."""
    db_signal = db.query(ActiveSignal).filter(ActiveSignal.signal_id == signal_id).first()
    if db_signal:
        db.delete(db_signal)
        db.commit()
      
