# src/database/models.py

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
import os

from dotenv import load_dotenv
load_dotenv()

# Load DB URL from .env or use SQLite fallback
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mydb.db")

# SQLAlchemy setup
Base = declarative_base()
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# === TABLE 1: Completed Trades ===

class CompletedTrade(Base):
    __tablename__ = "completed_trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    action = Column(String, nullable=False)        # BUY or SELL
    confidence = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# === TABLE 2: Cached Economic News ===

class CachedNews(Base):
    __tablename__ = "cached_news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# === Function to Initialize Tables ===

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
