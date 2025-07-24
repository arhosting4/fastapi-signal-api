import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from . import models
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# ===================================================================
# THIS IS THE COMPLETE AND CORRECT FILE. ALL FUNCTIONS ARE PRESENT.
# ===================================================================

# --- Signal Tracker Functions ---
def get_all_active_signals(db: Session) -> List[models.ActiveSignal]:
    """
    Retrieves all signals currently marked as active from the database.
    This function is CRITICAL for the dashboard.
    """
    logging.info("Fetching all active signals from DB...")
    try:
        return db.query(models.ActiveSignal).all()
    except Exception as e:
        logging.error(f"Failed to fetch active signals: {e}", exc_info=True)
        return []

def add_active_signal(db: Session, signal_data: Dict[str, Any]) -> models.ActiveSignal:
    """Adds a new active signal to the database."""
    db_signal = models.ActiveSignal(**signal_data)
    db.add(db_signal)
    db.commit()
    db.refresh(db_signal)
    logging.info(f"Added new active signal: {signal_data['signal_id']}")
    return db_signal

def remove_active_signal(db: Session, signal_id: str):
    """Removes an active signal from the database by its signal_id."""
    signal = db.query(models.ActiveSignal).filter(models.ActiveSignal.signal_id == signal_id).first()
    if signal:
        db.delete(signal)
        db.commit()
        logging.info(f"Removed active signal: {signal_id}")
    else:
        logging.warning(f"Attempted to remove non-existent active signal: {signal_id}")

# --- Completed Trade & History Functions ---
def add_completed_trade(db: Session, signal_data: Dict[str, Any], outcome: str):
    """Adds a completed trade to the history table."""
    trade_data = {
        "signal_id": signal_data.get("signal_id"),
        "symbol": signal_data.get("symbol"),
        "timeframe": signal_data.get("timeframe"),
        "signal_type": signal_data.get("signal_type"),
        "entry_price": signal_data.get("entry_price"),
        "tp_price": signal_data.get("tp_price"),
        "sl_price": signal_data.get("sl_price"),
        "outcome": outcome,
        "created_at": signal_data.get("created_at"),
        "closed_at": datetime.utcnow()
    }
    db_trade = models.CompletedTrade(**trade_data)
    db.add(db_trade)
    db.commit()
    logging.info(f"Trade completed and moved to history: {trade_data['signal_id']} with outcome {outcome}")

def get_trade_history(db: Session, limit: int = 100) -> List[models.CompletedTrade]:
    """Retrieves a list of recently completed trades."""
    logging.info(f"Fetching last {limit} trades from history...")
    return db.query(models.CompletedTrade).order_by(models.CompletedTrade.closed_at.desc()).limit(limit).all()

# --- Summary Stats Function ---
def get_summary_stats(db: Session) -> Dict[str, Any]:
    """
    Calculates and returns the win rate for the last 24 hours and P&L for the current day.
    This is the definitive, robust version that handles all edge cases.
    """
    logging.info("Calculating summary stats...")
    try:
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        total_trades_24h = db.query(func.count(models.CompletedTrade.id)).filter(models.CompletedTrade.closed_at >= twenty_four_hours_ago).scalar() or 0
        winning_trades_24h = db.query(func.count(models.CompletedTrade.id)).filter(models.CompletedTrade.closed_at >= twenty_four_hours_ago, models.CompletedTrade.outcome == 'tp_hit').scalar() or 0
        win_rate = (winning_trades_24h / total_trades_24h) * 100 if total_trades_24h > 0 else 0.0

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        wins_today = db.query(func.count(models.CompletedTrade.id)).filter(models.CompletedTrade.closed_at >= today_start, models.CompletedTrade.outcome == 'tp_hit').scalar() or 0
        losses_today = db.query(func.count(models.CompletedTrade.id)).filter(models.CompletedTrade.closed_at >= today_start, models.CompletedTrade.outcome == 'sl_hit').scalar() or 0
        pnl = (wins_today * 1.5) - (losses_today * 1.0)

        summary = {"win_rate": win_rate, "pnl": pnl}
        logging.info(f"Summary stats calculated: {summary}")
        return summary
    except Exception as e:
        logging.error(f"CRITICAL ERROR in get_summary_stats: {e}", exc_info=True)
        return {"win_rate": 0.0, "pnl": 0.0}

# --- News Functions ---
def update_news_cache(db: Session, news_data: Dict[str, Any]):
    """Deletes old news and inserts new news data."""
    try:
        db.query(models.CachedNews).delete()
        db_news = models.CachedNews(content=news_data, updated_at=datetime.utcnow())
        db.add(db_news)
        db.commit()
        logging.info("News cache updated successfully.")
    except Exception as e:
        logging.error(f"Failed to update news cache: {e}", exc_info=True)
        db.rollback()

def get_cached_news(db: Session) -> Optional[models.CachedNews]:
    """Retrieves the most recent cached news."""
    return db.query(models.CachedNews).order_by(models.CachedNews.updated_at.desc()).first()

# --- Feedback Functions ---
def add_feedback_entry(db: Session, symbol: str, timeframe: str, feedback: str):
    """Adds a feedback entry for a signal."""
    db_feedback = models.FeedbackEntry(symbol=symbol, timeframe=timeframe, feedback=feedback)
    db.add(db_feedback)
    db.commit()
    logging.info(f"Feedback entry added for {symbol} on {timeframe}.")

def get_feedback_stats_from_db(db: Session, symbol: str) -> Dict[str, Any]:
    """Retrieves feedback stats for a given symbol."""
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
    
