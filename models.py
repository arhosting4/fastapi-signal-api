# filename: models.py

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import os

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
Base = declarative_base()

class ActiveTrade(Base):
    __tablename__ = 'active_trades'
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    signal = Column(String) # 'buy' or 'sell'
    timeframe = Column(String)
    entry_price = Column(Float)
    tp = Column(Float)
    sl = Column(Float)
    confidence = Column(Float)
    reason = Column(String)
    tier = Column(String)
    entry_time = Column(DateTime(timezone=True), server_default=func.now())

class CompletedTrade(Base):
    __tablename__ = 'completed_trades'
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    # --- اہم تبدیلی: 'signal' کو 'signal_type' سے تبدیل کیا گیا ---
    signal_type = Column(String) # 'buy' or 'sell'
    entry_price = Column(Float)
    close_price = Column(Float)
    tp = Column(Float)
    sl = Column(Float)
    outcome = Column(String) # 'tp_hit' or 'sl_hit'
    entry_time = Column(DateTime)
    close_time = Column(DateTime(timezone=True), server_default=func.now())

def create_db_and_tables():
    # Render.com پر، ہمیں ٹیبلز کو حذف کرنے کی ضرورت نہیں ہے، صرف نئی بنائیں
    # MetaData.drop_all(bind=engine) # اس لائن کو غیر فعال رکھیں
    Base.metadata.create_all(bind=engine)
    print("--- Database tables checked/created. ---")
    
