# filename: models.py

import os
import time
import logging
from sqlalchemy import (create_engine, Column, Integer, String, Float, DateTime, JSON, func, Text) # Text شامل کیا گیا
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./signals.db")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}) if DATABASE_URL.startswith("sqlite") else create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ★★★ نیا ماڈل: فعال سگنلز کے لیے ★★★
class ActiveSignal(Base):
    __tablename__ = "active_signals"
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String, unique=True, index=True, nullable=False)
    symbol = Column(String, index=True, nullable=False)
    timeframe = Column(String)
    signal_type = Column(String)
    entry_price = Column(Float)
    tp_price = Column(Float)
    sl_price = Column(Float)
    confidence = Column(Float)
    reason = Column(Text) # لمبی وجوہات کے لیے Text استعمال کریں
    created_at = Column(DateTime, default=func.now())

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

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
    # ★★★ اضافی معلوماتی کالمز ★★★
    confidence = Column(Float)
    reason = Column(Text)
    closed_at = Column(DateTime, default=func.now())

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class FeedbackEntry(Base):
    __tablename__ = "feedback_entries"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    timeframe = Column(String)
    feedback = Column(String)
    created_at = Column(DateTime, default=func.now())

class CachedNews(Base):
    __tablename__ = "cached_news"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(JSON)
    updated_at = Column(DateTime, default=func.now())

def create_db_and_tables():
    lock_file_path = "/tmp/db_lock"
    for _ in range(10):
        try:
            fd = os.open(lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                logger.info("ڈیٹا بیس لاک حاصل کر لیا۔ تمام ٹیبلز بنائے جا رہے ہیں...")
                Base.metadata.create_all(bind=engine) # یہ تمام ٹیبلز بنا دے گا بشمول نیا ActiveSignal
                logger.info("ٹیبلز کامیابی سے بن گئے۔")
            finally:
                os.close(fd)
                os.remove(lock_file_path)
            return
        except FileExistsError:
            logger.info("کوئی دوسرا ورکر ڈیٹا بیس بنا رہا ہے، 1 سیکنڈ انتظار کر رہا ہے...")
            time.sleep(1)
    logger.warning("ڈیٹا بیس لاک حاصل کرنے میں ناکام۔ شاید کوئی دوسرا ورکر پھنس گیا ہے۔")

