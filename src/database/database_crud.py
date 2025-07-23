from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
# This relative import is correct as models.py is in the same directory
from .models import CompletedTrade, FeedbackEntry, CachedNews, ActiveSignal

# --- All CRUD functions remain unchanged ---
# (تمام فنکشنز کا کوڈ وہی ہے جو پچھلی اپڈیٹ میں تھا، صرف امپورٹ کو یقینی بنایا گیا ہے)

def add_active_signal(db: Session, signal_data: Dict[str, Any]):
    db_signal = ActiveSignal(**signal_data)
    db.add(db_signal)
    db.commit()
    db.refresh(db_signal)
    return db_signal

def get_all_active_signals(db: Session) -> List[ActiveSignal]:
    return db.query(ActiveSignal).all()

def remove_active_signal(db: Session, signal_id: str):
    db_signal = db.query(ActiveSignal).filter(ActiveSignal.signal_id == signal_id).first()
    if db_signal:
        db.delete(db_signal)
        db.commit()
        return True
    return False

def add_completed_trade(db: Session, signal_data: ActiveSignal, outcome: str):
    db_trade = CompletedTrade(
        signal_id=signal_data.signal_id,
        symbol=signal_data.symbol,
        timeframe=signal_data.timeframe,
        signal_type=signal_data.signal_type,
        entry_price=signal_data.entry_price,
        tp_price=signal_data.tp_price,
        sl_price=signal_data.sl_price,
        outcome=outcome,
        created_at=signal_data.created_at,
        closed_at=datetime.utcnow()
    )
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade

def get_completed_trades(db: Session, limit: int = 100) -> List[CompletedTrade]:
    return db.query(CompletedTrade).order_by(CompletedTrade.closed_at.desc()).limit(limit).all()

def get_summary_stats(db: Session) -> Dict[str, Any]:
    now = datetime.utcnow()
    past_24_hours = now - timedelta(hours=24)
    trades_last_24h = db.query(CompletedTrade).filter(CompletedTrade.closed_at >= past_24_hours).all()
    total_trades = len(trades_last_24h)
    win_trades = sum(1 for trade in trades_last_24h if trade.outcome == 'tp_hit')
    win_rate_24h = (win_trades / total_trades * 100) if total_trades > 0 else 0
    today_pl = 0.0 
    return {"win_rate_24h": win_rate_24h, "today_pl": today_pl}

def add_feedback_entry(db: Session, symbol: str, timeframe: str, feedback: str):
    db_entry = FeedbackEntry(symbol=symbol, timeframe=timeframe, feedback=feedback, created_at=datetime.utcnow())
    db.add(db_entry)
    db.commit()

def get_cached_news(db: Session) -> Optional[Dict[str, Any]]:
    news_item = db.query(CachedNews).order_by(CachedNews.updated_at.desc()).first()
    return news_item.content if news_item else None

def update_news_cache(db: Session, news_data: Dict[str, Any]):
    db.query(CachedNews).delete()
    db_news = CachedNews(content=news_data, updated_at=datetime.utcnow())
    db.add(db_news)
    db.commit()
    
