# filename: models.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# 🧱 Base model (ORM mapping base)
Base = declarative_base()

# ================================================
# 🔧 Database Configuration (SQLite Example)
# ================================================
DATABASE_URL = "sqlite:///./test.db"  # ⬅️ If PostgreSQL: use postgresql://user:pass@host/dbname

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

# =============================================================================
# 🔑 ActiveSignal Model — Active / Open Trades
# =============================================================================
class ActiveSignal(Base):
    __tablename__ = "active_signals"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    entry_price = Column(Float)
    signal_type = Column(String)
    strategy = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# =============================================================================
# 📈 CompletedTrade Model — Closed Trades / History
# =============================================================================
class CompletedTrade(Base):
    __tablename__ = "completed_trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    entry_price = Column(Float)
    exit_price = Column(Float)
    status = Column(String)
    pnl = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

# =============================================================================
# 💬 FeedbackEntry Model — User/AI Feedback Records
# =============================================================================
class FeedbackEntry(Base):
    __tablename__ = "feedback_entries"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer)
    feedback = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

# =============================================================================
# 📰 CachedNews Model — News Cache for Frontend
# =============================================================================
class CachedNews(Base):
    __tablename__ = "cached_news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(Text)
    published_at = Column(DateTime, default=datetime.utcnow)
