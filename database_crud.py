# database_crud.py

from sqlalchemy.orm import Session
from sqlalchemy import desc # نزولی ترتیب کے لیے
from datetime import datetime
from typing import Dict, Any, List

# ہمارے ڈیٹا بیس کے ماڈلز
from src.database.models import CompletedTrade, FeedbackEntry

def add_completed_trade(db: Session, signal_data: Dict[str, Any], outcome: str):
    """ایک مکمل شدہ ٹریڈ کو ڈیٹا بیس میں شامل کرتا ہے۔"""
    required_keys = ['signal_id', 'symbol', 'timeframe', 'signal', 'price', 'tp', 'sl']
    if not all(key in signal_data for key in required_keys):
        print(f"--- DB_CRUD ERROR: Missing required keys in signal_data for add_completed_trade ---")
        return None

    db_trade = CompletedTrade(
        signal_id=signal_data['signal_id'],
        symbol=signal_data['symbol'],
        timeframe=signal_data['timeframe'],
        signal_type=signal_data['signal'],
        entry_price=signal_data['price'],
        tp_price=signal_data['tp'],
        sl_price=signal_data['sl'],
        outcome=outcome,
        closed_at=datetime.utcnow()
    )
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    print(f"--- DB_CRUD SUCCESS: Added completed trade {db_trade.signal_id} to database. ---")
    return db_trade

def add_feedback_entry(db: Session, symbol: str, timeframe: str, feedback: str):
    """ایک فیڈ بیک اندراج کو ڈیٹا بیس میں شامل کرتا ہے۔"""
    db_feedback = FeedbackEntry(
        symbol=symbol,
        timeframe=timeframe,
        feedback=feedback
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    print(f"--- DB_CRUD SUCCESS: Added feedback '{feedback}' for {symbol} to database. ---")
    return db_feedback

# --- نئی تبدیلی: تاریخ حاصل کرنے کا فنکشن ---
def get_completed_trades(db: Session, limit: int = 100) -> List[CompletedTrade]:
    """
    ڈیٹا بیس سے تازہ ترین مکمل شدہ ٹریڈز حاصل کرتا ہے۔
    """
    print(f"--- DB_CRUD INFO: Fetching last {limit} completed trades from database. ---")
    # تازہ ترین ٹریڈز کو سب سے اوپر دکھانے کے لیے نزولی ترتیب کا استعمال کریں
    return db.query(CompletedTrade).order_by(desc(CompletedTrade.closed_at)).limit(limit).all()

