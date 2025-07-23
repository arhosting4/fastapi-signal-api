from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
import os

# Environment-based SQLite (or update with PostgreSQL if needed)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./signals.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ✅ Table for completed trades
class CompletedTrade(Base):
    __tablename__ = "completed_trades"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    timeframe = Column(String)
    entry_price = Column(Float)
    exit_price = Column(Float)
    profit = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

# ✅ Table for user feedback entries
class FeedbackEntry(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    timeframe = Column(String)
    feedback = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

# ✅ Table for economic news cache
class CachedNews(Base):
    __tablename__ = "cached_news"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    impact = Column(String)
    time = Column(String)
    currency = Column(String)
    forecast = Column(String)
    actual = Column(String)
    previous = Column(String)
    cached_at = Column(DateTime, default=datetime.utcnow)

# ✅ Create all tables in DB
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
