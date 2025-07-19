# database_crud.py

from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime
from typing import Dict, Any, List, Optional

# --- اہم تبدیلی: models کو یہاں امپورٹ کریں ---
from src.database.models import CompletedTrade, FeedbackEntry, CachedNews

# --- نیا فنکشن جو trainerai استعمال کرے گا ---
def get_feedback_stats_from_db(db: Session, symbol: str) -> Dict[str, Any]:
    """
    ڈیٹا بیس سے کسی مخصوص علامت کے لیے فیڈ بیک کے اعداد و شمار حاصل کرتا ہے۔
    """
    # --- اہم تبدیلی: پرنٹ پیغام کو ہٹا دیا گیا ہے تاکہ لاگز صاف رہیں ---
    correct_count = db.query(func.count(FeedbackEntry.id)).filter(
        FeedbackEntry.symbol == symbol,
        FeedbackEntry.feedback == 'correct'
    ).scalar()

    incorrect_count = db.query(func.count(FeedbackEntry.id)).filter(
        FeedbackEntry.symbol == symbol,
        FeedbackEntry.feedback == 'incorrect'
    ).scalar()
    
    total = correct_count + incorrect_count
    accuracy = (correct_count / total) * 100 if total > 0 else None

    return {
        "total": total,
        "accuracy": round(accuracy, 2) if accuracy is not None else 50.0, # اگر کوئی ڈیٹا نہیں تو 50 مانیں
        "correct": correct_count,
        "incorrect": incorrect_count,
    }

def add_completed_trade(db: Session, signal_data: Dict[str, Any], outcome: str):
    # یہ فنکشن ویسا ہی رہے گا
    required_keys = ['signal_id', 'symbol', 'timeframe', 'signal', 'price', 'tp', 'sl']
    if not all(key in signal_data for key in required_keys): return None
    db_trade = CompletedTrade(
        signal_id=signal_data['signal_id'], symbol=signal_data['symbol'],
        timeframe=signal_data['timeframe'], signal_type=signal_data['signal'],
        entry_price=signal_data['price'], tp_price=signal_data['tp'],
        sl_price=signal_data['sl'], outcome=outcome, closed_at=datetime.utcnow()
    )
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade

def add_feedback_entry(db: Session, symbol: str, timeframe: str, feedback: str):
    # یہ فنکشن ویسا ہی رہے گا
    db_feedback = FeedbackEntry(symbol=symbol, timeframe=timeframe, feedback=feedback)
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

def get_completed_trades(db: Session, limit: int = 100) -> List[CompletedTrade]:
    # یہ فنکشن ویسا ہی رہے گا
    return db.query(CompletedTrade).order_by(desc(CompletedTrade.closed_at)).limit(limit).all()

def update_news_cache(db: Session, news_data: Dict[str, Any]):
    # یہ فنکشن ویسا ہی رہے گا
    db.query(CachedNews).delete()
    db_news = CachedNews(content=news_data, updated_at=datetime.utcnow())
    db.add(db_news)
    db.commit()
    return db_news

def get_cached_news(db: Session) -> Optional[Dict[str, Any]]:
    # یہ فنکشن ویسا ہی رہے گا
    news_item = db.query(CachedNews).order_by(desc(CachedNews.updated_at)).first()
    return news_item.content if news_item else None
                                                   
