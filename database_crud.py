from datetime import datetime
from sqlalchemy.orm import Session
from src.database.models import CompletedTrade, FeedbackEntry, CachedNews, LiveSignal
from src.database.database import SessionLocal


# ✅ Save completed trade
def save_completed_trade(trade: dict):
    db: Session = SessionLocal()
    try:
        new_trade = CompletedTrade(
            symbol=trade["symbol"],
            entry_price=trade["entry_price"],
            exit_price=trade["exit_price"],
            profit=trade["profit"],
            timestamp=datetime.utcnow(),
        )
        db.add(new_trade)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving trade: {e}")
    finally:
        db.close()


# ✅ Save feedback entry
def save_feedback(feedback: dict):
    db: Session = SessionLocal()
    try:
        entry = FeedbackEntry(
            username=feedback["username"],
            message=feedback["message"],
            timestamp=datetime.utcnow(),
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving feedback: {e}")
    finally:
        db.close()


# ✅ Update or create news cache (used by sentinel.py)
def update_news_cache(news_list: list[dict]):
    db: Session = SessionLocal()
    try:
        db.query(CachedNews).delete()  # Clear old cache
        for item in news_list:
            cached = CachedNews(
                title=item.get("title"),
                content=item.get("content"),
                source=item.get("source", "Unknown"),
                published_at=item.get("published_at", datetime.utcnow()),
            )
            db.add(cached)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error updating news cache: {e}")
    finally:
        db.close()


# ✅ Retrieve cached news
def get_cached_news():
    db: Session = SessionLocal()
    try:
        return db.query(CachedNews).order_by(CachedNews.published_at.desc()).all()
    finally:
        db.close()


# ✅ Get all live signals
def get_all_signals():
    db: Session = SessionLocal()
    try:
        return db.query(LiveSignal).order_by(LiveSignal.timestamp.desc()).all()
    finally:
        db.close()
