# filename: database_crud.py
import json
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

# --- مقامی امپورٹس (فلیٹ اسٹرکچر) ---
from models import ActiveTrade, CompletedTrade

# ... (باقی تمام کوڈ جیسا ہے ویسا ہی رہے گا، صرف امپورٹ کو یقینی بنانا تھا)
# (The rest of the code in this file remains the same)
# ... (I will include the full code to be safe)

NEWS_CACHE_FILE = "data/news_cache.json"

def add_active_trade_to_db(db: Session, signal_data: dict) -> bool:
    existing_trade = db.query(ActiveTrade).filter(ActiveTrade.symbol == signal_data["symbol"]).first()
    if existing_trade:
        if existing_trade.signal == signal_data["signal"]:
            print(f"--- INFO: Signal for {signal_data['symbol']} is already active. Not adding duplicate. ---")
            return False
        else:
            print(f"--- INFO: Flipping signal for {signal_data['symbol']}. Removing old one. ---")
            db.delete(existing_trade)
            db.commit()

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
    print(f"--- SUCCESS: Added new active trade for {signal_data['symbol']} to DB. ---")
    return True

def get_all_active_trades_from_db(db: Session):
    return db.query(ActiveTrade).all()

def move_trade_to_completed(db: Session, trade_id: int, outcome: str, close_price: float):
    active_trade = db.query(ActiveTrade).filter(ActiveTrade.id == trade_id).first()
    if not active_trade:
        return

    completed_trade = CompletedTrade(
        symbol=active_trade.symbol,
        signal=active_trade.signal,
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
    return db.query(CompletedTrade).order_by(desc(CompletedTrade.close_time)).limit(limit).all()

def get_feedback_stats_from_db(db: Session, symbol: str):
    trades = db.query(CompletedTrade).filter(CompletedTrade.symbol == symbol).all()
    total = len(trades)
    if total == 0:
        return {"total": 0, "accuracy": 50.0}
    
    wins = sum(1 for trade in trades if trade.outcome == "tp_hit")
    accuracy = (wins / total) * 100
    return {"total": total, "accuracy": accuracy}

def get_news_from_cache():
    try:
        with open(NEWS_CACHE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
        
