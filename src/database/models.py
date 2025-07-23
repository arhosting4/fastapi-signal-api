# filename: src/database/models.py

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class CompletedTrade(Base):
    __tablename__ = "completed_trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    timeframe = Column(String)
    direction = Column(String)
    entry_price = Column(Float)
    exit_price = Column(Float)
    profit_loss = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class CachedNews(Base):
    __tablename__ = "cached_news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    impact = Column(String)
    country = Column(String)
    time = Column(String)
    date = Column(String)

class FeedbackEntry(Base):
    __tablename__ = "feedback_entries"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    timeframe = Column(String, nullable=False)
    feedback = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
