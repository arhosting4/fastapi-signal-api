# filename: models.py

import os
import logging
from sqlalchemy import (create_engine, Column, Integer, String, Float, DateTime, JSON, func)
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./signals.db")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# کنکشن کی ترتیبات
engine_args = {}
if not DATABASE_URL.startswith("sqlite"):
    engine_args = {
        "pool_size": 10,
        "max_overflow": 2,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    **engine_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ★★★ JobLock ٹیبل کو یہاں سے ہٹا دیا گیا ہے ★★★

class ActiveSignal(Base):
    __tablename__ = "active_signals"
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String, unique=True, index=True, nullable=False)
    symbol = Column(String, index=True, nullable=False)
    timeframe = Column(String, default="15min")
    signal_type = Column(String)
    entry_price = Column(Float)
    tp_price = Column(Float)
    sl_price = Column(Float)
    confidence = Column(Float)
    reason = Column(String)
    component_scores = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def as_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if isinstance(d.get('created_at'), datetime):
            d['created_at'] = d['created_at'].isoformat()
        if isinstance(d.get('updated_at'), datetime):
            d['updated_at'] = d['updated_at'].isoformat()
        return d

class CompletedTrade(Base):
    __tablename__ = "completed_trades"
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String, unique=True, index=True, nullable=False)
    symbol = Column(String, index=True, nullable=False)
    timeframe = Column(String)
    signal_type = Column(String)
    entry_price = Column(Float)
    tp_price = Column(Float)
    sl_price = Column(Float)
    close_price = Column(Float, nullable=True)
    reason_for_closure = Column(String, nullable=True)
    outcome = Column(String, index=True)
    confidence = Column(Float)
    reason = Column(String)
    closed_at = Column(DateTime, default=datetime.utcnow)
    
    def as_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if isinstance(d.get('closed_at'), datetime):
            d['closed_at'] = d['closed_at'].isoformat()
        return d

class FeedbackEntry(Base):
    __tablename__ = "feedback_entries"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    timeframe = Column(String)
    feedback = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class CachedNews(Base):
    __tablename__ = "cached_news"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(JSON)
    updated_at = Column(DateTime, default=datetime.utcnow)

def create_db_and_tables():
    """
    ڈیٹا بیس اور تمام ٹیبلز بناتا ہے۔
    """
    try:
        logger.info("ڈیٹا بیس اور ٹیبلز کی حالت کی تصدیق کی جا رہی ہے...")
        Base.metadata.create_all(bind=engine)
        logger.info("ٹیبلز کامیابی سے بنائے یا تصدیق کیے گئے۔")
    except Exception as e:
        logger.error(f"ڈیٹا بیس بنانے میں ایک غیر متوقع خرابی: {e}", exc_info=True)
        # اگر خرابی آتی ہے تو ایپ کو کریش ہونے سے روکنے کے لیے اسے پکڑیں
        # پیداواری ماحول میں، آپ یہاں دوبارہ کوشش کرنے کی منطق شامل کر سکتے ہیں
        pass
