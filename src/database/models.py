import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ✅ Trade Data Model
class CompletedTrade(Base):
    __tablename__ = "completed_trades"
    id = Column(Integer, primary_key=True, index=True)
    signal = Column(String)
    entry_price = Column(Float)
    exit_price = Column(Float)
    profit_loss = Column(Float)
    timestamp = Column(DateTime)

# ✅ User Feedback Model
class FeedbackEntry(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    feedback = Column(String)
    timestamp = Column(DateTime)

# ✅ News Cache Model
class CachedNews(Base):
    __tablename__ = "cached_news"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(String)
    published_at = Column(DateTime)

# ✅ Create Tables Function
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
