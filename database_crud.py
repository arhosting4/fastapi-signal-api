# filename: database_crud.py

from sqlalchemy.orm import Session
from models import ActiveSignal, NewsCache

def get_all_active_signals_from_db(db: Session):
    """
    Retrieve all currently active signals (is_active=True) from the database.
    Used by hunter/guardian engines to filter pairs.
    """
    return db.query(ActiveSignal).filter(ActiveSignal.is_active == True).all()

def update_news_cache_in_db(db: Session, news_obj):
    """
    Create or update the news cache in NewsCache table.
    Used by sentinel.py when updating/replacing all news cache by symbol.
    """
    obj = db.query(NewsCache).first()
    if not obj:
        obj = NewsCache()
    obj.articles_by_symbol = news_obj.get("articles_by_symbol")
    obj.updated_at = news_obj.get("updated_at")  # You can use datetime.utcnow() as well
    db.add(obj)
    db.commit()

def get_cached_news(db: Session):
    """
    Fetch cached news (grouped by symbol) from NewsCache table.
    """
    obj = db.query(NewsCache).first()
    if obj:
        return {"articles_by_symbol": obj.articles_by_symbol}
    return {}

# اگر ضرورت ہو تو یہاں مزید helper methods آسانی سے ایڈ کیے جا سکتے ہیں،
# مثلاً get_all_closed_signals_from_db، یا archive_signal وغیرہ۔
