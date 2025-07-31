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

# کنکشن آرگیومنٹس کو درست کیا گیا
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}) if "sqlite" in DATABASE_URL else create_engine(DATABASE_URL)
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
    # ★★★ نیا کالم شامل کیا گیا ★★★
    # یہ ہر انڈیکیٹر کے اسکور کو ذخیرہ کرے گا تاکہ AI سیکھ سکے
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
    # ★★★ نئے کالمز شامل کیے گئے ★★★
    close_price = Column(Float, nullable=True) # ٹریڈ کس قیمت پر بند ہوئی
    reason_for_closure = Column(String, nullable=True) # بند ہونے کی وجہ (e.g., "tp_hit", "sl_hit")
    outcome = Column(String, index=True) # نتیجہ (tp_hit, sl_hit)
    confidence = Column(Float)
    reason = Column(String)
    closed_at = Column(DateTime, default=datetime.utcnow)
    
    def as_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if isinstance(d.get('closed_at'), datetime):
            d['closed_at'] = d['closed_at'].isoformat()
        # as_dict میں دیگر تاریخوں کو ہینڈل کرنے کے لیے اضافی چیکس
        if d.get('created_at') and isinstance(d.get('created_at'), datetime):
            d['created_at'] = d['created_at'].isoformat()
        if d.get('updated_at') and isinstance(d.get('updated_at'), datetime):
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
    # یہ فنکشن ڈیٹا بیس اور ٹیبلز بناتا ہے
    # پیداواری ماحول میں، Alembic جیسا ٹول استعمال کرنا بہتر ہے
    logger.info("ڈیٹا بیس اور ٹیبلز کی حالت کی تصدیق کی جا رہی ہے...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("ٹیبلز کامیابی سے بنائے یا تصدیق کیے گئے۔")
    except Exception as e:
        logger.error(f"ڈیٹا بیس بنانے میں خرابی: {e}", exc_info=True)
        
