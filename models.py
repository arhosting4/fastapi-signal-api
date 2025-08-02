# filename: models.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Float, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()

class ActiveSignal(Base):
    __tablename__ = "active_signals"
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    signal_type = Column(String, nullable=False)
    component_scores = Column(JSON)    # Example: {"ema_cross": 1, "rsi_position": -1, ...}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    closed_at = Column(DateTime)  # Optional: when closed (TP/SL hit or manually closed)

class NewsCache(Base):
    __tablename__ = "news_cache"
    id = Column(Integer, primary_key=True)
    articles_by_symbol = Column(JSON)  # {symbol: [articles...], ...}
    updated_at = Column(DateTime, default=datetime.utcnow)

# --- DB INIT/SESSION ---
DATABASE_URL = "sqlite:///app.db"  # For development/testing. Use env-based string in production!
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Create tables if not present (for CLI or test use)"""
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("Database & tables created.")
  
