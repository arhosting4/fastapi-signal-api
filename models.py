from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ActiveSignal(Base):
    __tablename__ = "active_signals"
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String, unique=True, index=True, nullable=False)
    symbol = Column(String, index=True)
    timeframe = Column(String)
    signal_type = Column(String)
    entry_price = Column(Float)
    confidence = Column(Float)
    reason = Column(String)
    tp_price = Column(Float)
    sl_price = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class CompletedTrade(Base):
    __tablename__ = "completed_trades"
    id = Column(Integer, primary_key=True, index=True)
    # ===================================================================
    # FINAL AND CORRECTED VERSION
    # This adds the missing 'signal_id' column to the database model.
    # ===================================================================
    signal_id = Column(String, unique=True, index=True, nullable=False) # <--- یہ لائن شامل کی گئی ہے
    symbol = Column(String, index=True)
    timeframe = Column(String)
    signal_type = Column(String)
    entry_price = Column(Float)
    outcome = Column(String)
    created_at = Column(DateTime)
    closed_at = Column(DateTime, default=datetime.utcnow)

class CachedNews(Base):
    __tablename__ = "cached_news"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(JSON)
    updated_at = Column(DateTime, default=datetime.utcnow)

class FeedbackEntry(Base):
    __tablename__ = "feedback_entries"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    timeframe = Column(String)
    feedback = Column(String) # 'correct' or 'incorrect'
    created_at = Column(DateTime, default=datetime.utcnow)
    
