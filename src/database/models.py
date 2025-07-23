# filename: src/database/models.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
import os

# Use environment variable or fallback
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Base class for models
Base = declarative_base()

# Engine and Session setup
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ✅ 1. Live Signal Model
class LiveSignal(Base):
    __tablename__ = "live_signals"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    timeframe = Column(String)
    strategy = Column(String)
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

# ✅ 2. Completed Trade Model
class CompletedTrade(Base):
    __tablename__ = "completed_trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    timeframe = Column(String)
    strategy = Column(String)
    confidence = Column(Float)
    opened_at = Column(DateTime)
    closed_at = Column(DateTime)
    result = Column(String)  # "win", "loss", etc.
    profit_percent = Column(Float)

# ✅ 3. Feedback Model
class FeedbackEntry(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    timeframe = Column(String)
    feedback = Column(Text)
    submitted_at = Column(DateTime, default=datetime.utcnow)

# ✅ 4. Economic News Cache Table (Optional)
class NewsItem(Base):
    from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from .database import Base

class CachedNews(Base):
    __tablename__ = "cached_news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(100), default="Unknown")
    published_at = Column(DateTime, default=datetime.utcnow)
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    impact = Column(String)
    time = Column(String)
    country = Column(String)
    cached_at = Column(DateTime, default=datetime.utcnow)

# ✅ 5. Create all tables
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
