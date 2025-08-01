# filename: models.py

import logging
from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Float, Integer, JSON,
                        String, create_engine)
from sqlalchemy.orm import declarative_base, sessionmaker

# مقامی امپورٹس
from config import api_settings

logger = logging.getLogger(__name__)

# --- ڈیٹا بیس کنکشن ---

# اصلاح: DATABASE_URL کو استعمال کرنے سے پہلے اسے سٹرنگ میں تبدیل کریں
# pydantic کا PostgresDsn ایک خاص آبجیکٹ واپس کرتا ہے، سٹرنگ نہیں
db_url_str = str(api_settings.DATABASE_URL)

# چیک کریں کہ آیا ڈیٹا بیس SQLite ہے یا PostgreSQL
is_sqlite = db_url_str.startswith("sqlite")

# کنکشن کی ترتیبات
engine_args = {}
if not is_sqlite:
    # PostgreSQL کے لیے پولنگ کی ترتیبات
    engine_args = {
        "pool_size": 10,
        "max_overflow": 2,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

# ڈیٹا بیس انجن بنائیں
engine = create_engine(
    db_url_str,
    # SQLite کے لیے تھریڈ سیفٹی
    connect_args={"check_same_thread": False} if is_sqlite else {},
    **engine_args
)

# ڈیٹا بیس سیشن
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# SQLAlchemy کا بنیادی ماڈل
Base = declarative_base()

# --- ڈیٹا بیس ماڈلز ---

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
    is_new = Column(Boolean, default=True, nullable=False)

    def as_dict(self):
        """ماڈل آبجیکٹ کو ڈکشنری میں تبدیل کرتا ہے۔"""
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        # datetime آبجیکٹس کو ISO فارمیٹ سٹرنگ میں تبدیل کریں
        for key, value in d.items():
            if isinstance(value, datetime):
                d[key] = value.isoformat()
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
        """ماڈل آبجیکٹ کو ڈکشنری میں تبدیل کرتا ہے۔"""
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if isinstance(d.get('closed_at'), datetime):
            d['closed_at'] = d['closed_at'].isoformat()
        return d

class CachedNews(Base):
    __tablename__ = "cached_news"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(JSON)
    updated_at = Column(DateTime, default=datetime.utcnow)

def create_db_and_tables():
    """
    ڈیٹا بیس اور تمام ٹیبلز بناتا ہے اگر وہ موجود نہ ہوں۔
    """
    try:
        logger.info("ڈیٹا بیس اور ٹیبلز کی حالت کی تصدیق کی جا رہی ہے...")
        Base.metadata.create_all(bind=engine)
        logger.info("ٹیبلز کامیابی سے بنائے یا تصدیق کیے گئے۔")
    except Exception as e:
        logger.critical(f"ڈیٹا بیس بنانے میں ایک سنگین خرابی پیش آئی: {e}", exc_info=True)
        raise
    
