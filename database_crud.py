from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional, Dict, Any
from datetime import datetime

# ===================================================================
# FINAL AND CORRECTED VERSION FOR FLAT STRUCTURE
# This changes the relative import 'from . import models' to an absolute import.
# ===================================================================

# غلط لائن (اسے ہٹا دیں): from . import models
# درست لائن (اسے شامل کریں):
import models

from database_config import SessionLocal

# --- Signal and Trade Management ---

def add_active_signal(db: Session, signal_data: Dict[str, Any]):
    """Adds a new active signal to the database."""
    db_signal = models.ActiveSignal(**signal_data)
    db.add(db_signal)
    db.commit()
    db.refresh(db_signal)
    return db_signal

def get_all_active_signals(db: Session) -> List[models.ActiveSignal]:
    """Retrieves all active signals from the database."""
    return db.query(models.ActiveSignal).all()

def remove_active_signal(db: Session, signal_id: str):
    """Removes an active signal from the database by its ID."""
    db_signal = db.query(models.ActiveSignal).filter(models.ActiveSignal.signal_id == signal_id).first()
    if db_signal:
        db.delete(db_signal)
        db.commit()
    return db_signal

def add_completed_trade(db: Session, signal_data: Dict[str, Any], outcome: str):
    """Moves an active signal to the completed trades table with an outcome."""
    trade_data = {
        "signal_id": signal_data['signal_id'],
        "symbol": signal_data['symbol'],
        "timeframe": signal_data['timeframe'],
        "signal_type": signal_data['signal_type'],
        "entry_price": signal_data['entry_price'],
        "outcome": outcome,
        "created_at": signal_data['created_at'],
        "closed_at": datetime.utcnow()
    }
    db_trade = models.CompletedTrade(**trade_data)
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade

def get_trade_history(db: Session, limit: int = 100) -> List[models.CompletedTrade]:
    """Retrieves the most recent completed trades."""
    return db.query(models.CompletedTrade).order_by(desc(models.CompletedTrade.closed_at)).limit(limit).all()

# --- Summary Statistics ---

def get_summary_stats(db: Session) -> Dict[str, float]:
    """Calculates win rate and P/L for the summary cards."""
    # This is a placeholder. A real P/L calculation would be more complex.
    # For now, we focus on win rate.
    total_trades = db.query(func.count(models.CompletedTrade.id)).scalar() or 0
    wins = db.query(func.count(models.CompletedTrade.id)).filter(models.CompletedTrade.outcome == 'tp_hit').scalar() or 0
    
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0.0
    
    # Placeholder for P/L
    pnl = 0.0 
    
    return {"win_rate": win_rate, "pnl": pnl}

# --- News Cache ---

def update_news_cache(db: Session, news_data: Dict[str, Any]):
    """Updates or creates the news cache."""
    cache_entry = db.query(models.CachedNews).first()
    if cache_entry:
        cache_entry.content = news_data
        cache_entry.updated_at = datetime.utcnow()
    else:
        cache_entry = models.CachedNews(content=news_data)
        db.add(cache_entry)
    db.commit()

def get_cached_news(db: Session) -> Optional[models.CachedNews]:
    """Retrieves the cached news."""
    return db.query(models.CachedNews).first()

# --- Feedback System ---

def add_feedback_entry(db: Session, symbol: str, timeframe: str, feedback: str):
    """Adds a feedback entry for a signal's outcome."""
    db_feedback = models.FeedbackEntry(
        symbol=symbol,
        timeframe=timeframe,
        feedback=feedback,
        created_at=datetime.utcnow()
    )
    db.add(db_feedback)
    db.commit()

def get_feedback_stats(db: Session, symbol: str) -> Dict[str, Any]:
    """Gets feedback statistics for a given symbol to calculate confidence."""
    total = db.query(func.count(models.FeedbackEntry.id)).filter_by(symbol=symbol).scalar() or 0
    correct = db.query(func.count(models.FeedbackEntry.id)).filter_by(symbol=symbol, feedback='correct').scalar() or 0
    incorrect = db.query(func.count(models.FeedbackEntry.id)).filter_by(symbol=symbol, feedback='incorrect').scalar() or 0
    accuracy = (correct / total) * 100 if total > 0 else 0
    return {
        "total": total,
        "correct": correct,
        "incorrect": incorrect,
        "accuracy": accuracy
    }
    
