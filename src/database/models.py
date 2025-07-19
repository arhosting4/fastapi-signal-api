from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, MetaData
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
import os

# --- ڈیٹا بیس کنکشن ---
# ہم یہاں دوبارہ URL حاصل کرتے ہیں تاکہ یہ ماڈیول آزادانہ طور پر کام کر سکے
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set for models.")

engine = create_engine(DATABASE_URL)
Base = declarative_base()

# --- ٹیبل 1: مکمل شدہ ٹریڈز ---
class CompletedTrade(Base):
    __tablename__ = 'completed_trades'

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String, unique=True, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False)
    signal_type = Column(String, nullable=False) # 'buy' or 'sell'
    entry_price = Column(Float, nullable=False)
    tp_price = Column(Float, nullable=False)
    sl_price = Column(Float, nullable=False)
    outcome = Column(String, nullable=False) # 'tp_hit', 'sl_hit', 'expired'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=False)

    def __repr__(self):
        return f"<CompletedTrade(id={self.id}, symbol='{self.symbol}', outcome='{self.outcome}')>"

# --- ٹیبل 2: فیڈ بیک اندراجات ---
class FeedbackEntry(Base):
    __tablename__ = 'feedback_entries'

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False)
    feedback = Column(String, nullable=False) # 'correct', 'incorrect', 'missed'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<FeedbackEntry(id={self.id}, symbol='{self.symbol}', feedback='{self.feedback}')>"

# --- یہ فنکشن ڈیٹا بیس میں ٹیبلز بنائے گا ---
def create_db_and_tables():
    print("--- Checking and creating database tables... ---")
    try:
        # MetaData.create_all صرف وہی ٹیبلز بناتا ہے جو پہلے سے موجود نہ ہوں
        Base.metadata.create_all(bind=engine)
        print("--- Database tables are ready. ---")
    except Exception as e:
        print(f"--- CRITICAL: Could not create database tables: {e} ---")
        raise

