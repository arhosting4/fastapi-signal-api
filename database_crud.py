from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from src.database.models import CompletedTrade, FeedbackEntry, CachedNews

# ✅ Get trade history from DB
def get_completed_trades(db: Session) -> List[dict]:
    trades = db.query(CompletedTrade).order_by(CompletedTrade.timestamp.desc()).all()
    return [
        {
            "symbol": trade.symbol,
            "timeframe": trade.timeframe,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "profit": trade.profit,
            "timestamp": trade.timestamp.isoformat()
        }
        for trade in trades
    ]

# ✅ Get news cache from DB
def get_cached_news(db: Session) -> List[dict]:
    news = db.query(CachedNews).order_by(CachedNews.cached_at.desc()).all()
    return [
        {
            "title": n.title,
            "impact": n.impact,
            "time": n.time,
            "currency": n.currency,
            "forecast": n.forecast,
            "actual": n.actual,
            "previous": n.previous,
            "cached_at": n.cached_at.isoformat()
        }
        for n in news
    ]

# ✅ Save news to DB (used by update_economic_calendar_cache)
def cache_news_entries(db: Session, news_list: List[dict]):
    db.query(CachedNews).delete()
    for news in news_list:
        cached = CachedNews(
            title=news.get("title", ""),
            impact=news.get("impact", ""),
            time=news.get("time", ""),
            currency=news.get("currency", ""),
            forecast=news.get("forecast", ""),
            actual=news.get("actual", ""),
            previous=news.get("previous", ""),
            cached_at=datetime.utcnow()
        )
        db.add(cached)
    db.commit()

# ✅ Add a completed trade to DB
def add_completed_trade(db: Session, symbol: str, timeframe: str, entry: float, exit: float, profit: float):
    trade = CompletedTrade(
        symbol=symbol,
        timeframe=timeframe,
        entry_price=entry,
        exit_price=exit,
        profit=profit,
        timestamp=datetime.utcnow()
    )
    db.add(trade)
    db.commit()

# ✅ Save user feedback to DB
def add_feedback_entry(db: Session, symbol: str, timeframe: str, feedback: str) -> Optional[FeedbackEntry]:
    entry = FeedbackEntry(
        symbol=symbol,
        timeframe=timeframe,
        feedback=feedback,
        timestamp=datetime.utcnow()
    )
    db.add(entry)
    db.commit()
    return entry
