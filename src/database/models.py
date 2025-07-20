from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
import os

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set for models.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class CompletedTrade(Base):
    __tablename__ = 'completed_trades'
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String, unique=True, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False)
    signal_type = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    tp_price = Column(Float, nullable=False)
    sl_price = Column(Float, nullable=False)
    outcome = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=False)

class FeedbackEntry(Base):
    __tablename__ = 'feedback_entries'
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False)
    feedback = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CachedNews(Base):
    __tablename__ = 'cached_news'
    id = Column(Integer, primary_key=True)
    content = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

def create_db_and_tables():
    print("--- Checking and creating database tables... ---")
    try:
        Base.metadata.create_all(bind=engine)
        print("--- Database tables are ready. ---")
    except Exception as e:
        print(f"--- CRITICAL: Could not create database tables: {e} ---")
        raise
        
