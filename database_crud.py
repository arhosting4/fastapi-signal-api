# filename: database_crud.py

from sqlalchemy.orm import Session
from typing import Optional, List
from src.database.models import CompletedTrade, CachedNews, FeedbackEntry

# -------------------------
# ✅ TRADE HISTORY FUNCTIONS
# -------------------------

def get_completed_trades(db: Session) -> List[CompletedTrade]:
    return db.query(CompletedTrade).order_by(CompletedTrade.timestamp.desc()).all()

# -------------------------
# ✅ NEWS CACHE FUNCTIONS
# -------------------------

def get_cached_news(db: Session) -> List[CachedNews]:
    return db.query(CachedNews).all()

def clear_cached_news(db: Session):
    db.query(CachedNews).delete()
    db.commit()

def add_news_entry(db: Session, title: str, impact: str, country: str, time: str, date: str):
    news = CachedNews(
        title=title,
        impact=impact,
        country=country,
        time=time,
        date=date
    )
    db.add(news)
    db.commit()

# -------------------------
# ✅ FEEDBACK FUNCTIONS
# -------------------------

def add_feedback_entry(db: Session, symbol: str, timeframe: str, feedback: str) -> Optional[FeedbackEntry]:
    entry = FeedbackEntry(
        symbol=symbol,
        timeframe=timeframe,
        feedback=feedback
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

def get_all_feedback(db: Session) -> List[FeedbackEntry]:
    return db.query(FeedbackEntry).order_by(FeedbackEntry.timestamp.desc()).all()
