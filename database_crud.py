from sqlalchemy.orm import Session
from src.database.models import CompletedTrade, FeedbackEntry, CachedNews, LiveSignal
from datetime import datetime


# ✅ Save a new completed trade
def save_trade(db: Session, trade_data: dict):
    trade = CompletedTrade(**trade_data)
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


# ✅ Get all completed trades
def get_all_trades(db: Session):
    return db.query(CompletedTrade).order_by(CompletedTrade.timestamp.desc()).all()


# ✅ Save feedback entry
def save_feedback(db: Session, feedback_data: dict):
    feedback = FeedbackEntry(**feedback_data)
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


# ✅ Save cached news
def cache_news_item(db: Session, news_data: dict):
    news_item = CachedNews(**news_data)
    db.add(news_item)
    db.commit()
    db.refresh(news_item)
    return news_item


# ✅ Get cached news
def get_cached_news(db: Session, limit: int = 10):
    return db.query(CachedNews).order_by(CachedNews.published_at.desc()).limit(limit).all()


# ✅ Save live signal (if needed)
def save_live_signal(db: Session, signal_data: dict):
    signal = LiveSignal(**signal_data)
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


# ✅ Get all live signals
def get_all_live_signals(db: Session):
    return db.query(LiveSignal).order_by(LiveSignal.created_at.desc()).all()
