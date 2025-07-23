# filename: src/database/models.py

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
import os

# Base declaration
Base = declarative_base()

# SQLite database (You can replace with PostgreSQL/MySQL URI from .env)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./scalp_signals.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 📌 Table: Completed Trades History
class CompletedTrade(Base):
    __tablename__ = "completed_trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    entry_price = Column(String)
    exit_price = Column(String)
    profit_loss = Column(String)
    time_closed = Column(DateTime, default=datetime.utcnow)
    strategy = Column(String, default="unknown")
    timeframe = Column(String, default="1m")


# 📌 Table: Feedback Entries
class FeedbackEntry(Base):
    __tablename__ = "feedback_entries"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    timeframe = Column(String)
    feedback = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


# 📌 Table: Cached Economic News
class CachedNews(Base):
    __tablename__ = "cached_news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    impact = Column(String)
    event_time = Column(DateTime)
    country = Column(String)
    actual = Column(String)
    forecast = Column(String)
    previous = Column(String)
    cached_at = Column(DateTime, default=datetime.utcnow)


# 📌 Create all tables
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
