# filename: database_crud.py

import json
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

from models import ActiveTrade, CompletedTrade

NEWS_CACHE_FILE = "data/news_cache.json"

def add_active_trade_to_db(db: Session, signal_data: dict) -> bool:
    """
    Active trade کو database میں add کرتا ہے
    """
    existing_trade = db.query(ActiveTrade).filter(
        ActiveTrade.symbol == signal_data["symbol"],
        ActiveTrade.timeframe == signal_data["timeframe"]
    ).first()

    if existing_trade:
        if existing_trade.signal == signal_data["signal"]:
            # Same signal, update existing trade
            existing_trade.entry_price = signal_data["price"]
            existing_trade.tp = signal_data["tp"]
            existing_trade.sl = signal_data["sl"]
            existing_trade.confidence = signal_data["confidence"]
            existing_trade.reason = signal_data["reason"]
            existing_trade.tier = signal_data["tier"]
            db.commit()
            return False  # Not a new trade
        else:
            # Different signal, remove old and add new
            db.delete(existing_trade)
    
    new_trade = ActiveTrade(
        symbol=signal_data["symbol"],
        signal=signal_data["signal"],
        timeframe=signal_data["timeframe"],
        entry_price=signal_data["price"],
        tp=signal_data["tp"],
        sl=signal_data["sl"],
        confidence=signal_data["confidence"],
        reason=signal_data["reason"],
        tier=signal_data["tier"]
    )
    db.add(new_trade)
    db.commit()
    return True  # New trade added

def get_all_active_trades_from_db(db: Session):
    """
    تمام active trades کو database سے retrieve کرتا ہے
    """
    return db.query(ActiveTrade).all()

def move_trade_to_completed(db: Session, trade_id: int, outcome: str, close_price: float):
    """
    Active trade کو completed trades میں move کرتا ہے
    """
    active_trade = db.query(ActiveTrade).filter(ActiveTrade.id == trade_id).first()
    if not active_trade:
        return

    completed_trade = CompletedTrade(
        symbol=active_trade.symbol,
        signal=active_trade.signal,  # یہاں signal column کا نام 'signal' ہی ہے
        entry_price=active_trade.entry_price,
        close_price=close_price,
        tp=active_trade.tp,
        sl=active_trade.sl,
        outcome=outcome,
        entry_time=active_trade.entry_time,
        close_time=datetime.utcnow()
    )
    db.add(completed_trade)
    db.delete(active_trade)
    db.commit()

def get_completed_trades_from_db(db: Session, limit: int = 50):
    """
    Completed trades کو database سے retrieve کرتا ہے
    """
    return db.query(CompletedTrade).order_by(desc(CompletedTrade.close_time)).limit(limit).all()

def get_feedback_stats_from_db(db: Session, symbol: str):
    """
    کسی specific symbol کے لیے feedback statistics calculate کرتا ہے
    """
    trades = db.query(CompletedTrade).filter(CompletedTrade.symbol == symbol).all()
    total = len(trades)
    if total == 0:
        return {"total": 0, "accuracy": 50.0}
    
    wins = sum(1 for trade in trades if trade.outcome == "tp_hit")
    accuracy = (wins / total) * 100
    return {"total": total, "accuracy": accuracy}

def get_news_from_cache():
    """
    News cache سے latest news retrieve کرتا ہے
    """
    try:
        with open(NEWS_CACHE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
