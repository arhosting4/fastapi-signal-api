# filename: models.py

from sqlalchemy import Column, Integer, String, Float, DateTime, create_engine
from sqlalchemy.sql import func
from datetime import datetime

# --- اہم تبدیلی: Base کو database_config سے امپورٹ کریں ---
from database_config import Base, engine

class ActiveTrade(Base):
    __tablename__ = "active_trades"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    signal = Column(String)
    timeframe = Column(String)
    entry_price = Column(Float)
    tp = Column(Float)
    sl = Column(Float)
    confidence = Column(Float)
    reason = Column(String)
    tier = Column(String)
    entry_time = Column(DateTime, default=datetime.utcnow)

class CompletedTrade(Base):
    __tablename__ = "completed_trades"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    signal = Column(String)
    entry_price = Column(Float)
    close_price = Column(Float)
    tp = Column(Float)
    sl = Column(Float)
    outcome = Column(String) # e.g., "tp_hit", "sl_hit"
    entry_time = Column(DateTime)
    close_time = Column(DateTime, default=datetime.utcnow)

def create_db_and_tables():
    # یہ فنکشن تمام ٹیبلز بنائے گا اگر وہ موجود نہیں ہیں۔
    print("--- Creating database tables if they don't exist... ---")
    Base.metadata.create_all(bind=engine)
    print("--- Tables created/verified. ---")

