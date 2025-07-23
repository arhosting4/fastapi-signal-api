from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from datetime import datetime

# Create database connection
SQLALCHEMY_DATABASE_URL = "sqlite:///./signal.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declare base
Base = declarative_base()

# ===========================
# ✅ Trade table
# ===========================
class CompletedTrade(Base):
    __tablename__ = "completed_trades"

    id = Column(Integer, primary_key=True, index=True)
    trade_date = Column(String, index=True)
    pair = Column(String)
    signal_type = Column(String)
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    result = Column(String)
    duration = Column(String)
    profit_loss = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

# ===========================
# ✅ Feedback table
# ===========================
class FeedbackEntry(Base):
    __tablename__ = "feedback_entries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# ===========================
# ✅ Cached News table
# ===========================
class CachedNews(Base):
    __tablename__ = "cached_news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    url = Column(String)
    source = Column(String)
    published_at = Column(DateTime)
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

# ===========================
# ✅ NewsItem for frontend/news.html API
# ===========================
class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(Text)
    url = Column(String)
    source = Column(String)
    published_at = Column(DateTime)
    timestamp = Column(DateTime, default=datetime.utcnow)

# ===========================
# ✅ Live Signal table (Optional for charts)
# ===========================
class LiveSignal(Base):
    __tablename__ = "live_signals"

    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String)
    signal_type = Column(String)
    price = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

# ===========================
# ✅ Create all tables
# ===========================
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
