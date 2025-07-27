# filename: models.py

import os
import time
import logging
from sqlalchemy import (create_engine, Column, Integer, String, Float, DateTime, JSON, func, Boolean)
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./signals.db")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}) if DATABASE_URL.startswith("sqlite") else create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ★★★ اپ ڈیٹ شدہ فنکشن ★★★
    def as_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        # datetime آبجیکٹس کو ISO اسٹرنگ میں تبدیل کریں
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
    outcome = Column(String, index=True)
    confidence = Column(Float)
    reason = Column(String)
    closed_at = Column(DateTime, default=datetime.utcnow)
    
    # ★★★ اپ ڈیٹ شدہ فنکشن ★★★
    def as_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        # datetime آبجیکٹ کو ISO اسٹرنگ میں تبدیل کریں
        if isinstance(d.get('closed_at'), datetime):
            d['closed_at'] = d['closed_at'].isoformat()
        # احتیاط کے طور پر created_at/updated_at بھی شامل کر سکتے ہیں اگر وہ مستقبل میں شامل کیے جائیں
        if isinstance(d.get('created_at'), datetime):
            d['created_at'] = d['created_at'].isoformat()
        if isinstance(d.get('updated_at'), datetime):
            d['updated_at'] = d['updated_at'].isoformat()
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
    lock_file_path = "/tmp/db_lock"
    try:
        fd = os.open(lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            logger.info("ڈیٹا بیس لاک حاصل کر لیا۔ تمام ٹیبلز بنائے جا رہے ہیں...")
            Base.metadata.create_all(bind=engine)
            logger.info("ٹیبلز کامیابی سے بن گئے۔")
        finally:
            os.close(fd)
            os.remove(lock_file_path)
    except FileExistsError:
        logger.info("کوئی دوسرا ورکر ڈیٹا بیس بنا رہا ہے، انتظار کیا جا رہا ہے۔")
        time.sleep(2)
    except Exception as e:
        logger.error(f"ڈیٹا بیس بنانے میں خرابی: {e}", exc_info=True)
        
