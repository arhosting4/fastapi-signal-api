# filename: models.py

import os
import time
import logging
from sqlalchemy import (create_engine, Column, Integer, String, Float, DateTime, JSON, func)
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

# --- ماڈلز ویسے ہی رہیں گے ---
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
    closed_at = Column(DateTime, default=func.now())
    def as_dict(self): return {c.name: getattr(self, c.name) for c in self.__table__.columns}

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

# --- اپ ڈیٹ شدہ فنکشن ---
def create_db_and_tables():
    """
    ریس کنڈیشن سے بچنے کے لیے فائل لاک کا استعمال کرتے ہوئے ڈیٹا بیس ٹیبلز بناتا ہے۔
    """
    lock_file_path = "/tmp/db_lock" # Render.com پر /tmp ڈائرکٹری قابل تحریر ہے
    
    # 10 سیکنڈ تک لاک حاصل کرنے کی کوشش کریں
    for _ in range(10):
        try:
            # O_CREAT | O_EXCL اس بات کو یقینی بناتا ہے کہ فائل صرف اسی صورت میں بنے گی اگر وہ پہلے سے موجود نہ ہو
            # یہ ایک ایٹمی (atomic) آپریشن ہے
            fd = os.open(lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            
            # --- لاک حاصل ہو گیا، اب ٹیبلز بنائیں ---
            try:
                logger.info("ڈیٹا بیس لاک حاصل کر لیا۔ ٹیبلز بنائے جا رہے ہیں...")
                Base.metadata.create_all(bind=engine)
                logger.info("ٹیبلز کامیابی سے بن گئے۔")
            finally:
                # کام مکمل ہونے پر لاک فائل کو بند کریں اور ہٹا دیں
                os.close(fd)
                os.remove(lock_file_path)
            return # فنکشن سے باہر نکلیں
            
        except FileExistsError:
            # اگر فائل پہلے سے موجود ہے، تو اس کا مطلب ہے کہ کوئی دوسرا ورکر ٹیبل بنا رہا ہے
            logger.info("کوئی دوسرا ورکر ڈیٹا بیس بنا رہا ہے، 1 سیکنڈ انتظار کر رہا ہے...")
            time.sleep(1)
            
    # اگر 10 سیکنڈ کے بعد بھی لاک فائل موجود ہے، تو شاید کوئی مسئلہ ہے
    logger.warning("ڈیٹا بیس لاک حاصل کرنے میں ناکام۔ شاید کوئی دوسرا ورکر پھنس گیا ہے۔")
    
