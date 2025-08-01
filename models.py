# filename: models.py

import logging
from datetime import datetime
from typing import Dict, Any

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, JSON, Boolean,
    event
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.engine import Engine

# مقامی امپورٹس
# کنفیگریشن کو مرکزی config.py سے درآمد کریں
from config import api_settings

logger = logging.getLogger(__name__)

# --- ڈیٹا بیس انجن اور سیشن کی ترتیب ---

# کنکشن کی ترتیبات کو ڈیٹا بیس کی قسم کی بنیاد پر منظم کریں
engine_args = {}
is_sqlite = api_settings.DATABASE_URL.startswith("sqlite")

if not is_sqlite:
    engine_args = {
        "pool_size": 10,
        "max_overflow": 2,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

# انجن بنائیں
engine = create_engine(
    api_settings.DATABASE_URL,
    # SQLite کے لیے تھریڈ سیفٹی کو یقینی بنائیں
    connect_args={"check_same_thread": False} if is_sqlite else {},
    **engine_args
)

# SQLite پر PRAGMA کو فعال کرنے کے لیے ایونٹ سنیں (کارکردگی کے لیے)
if is_sqlite:
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

# سیشن میکر
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# بنیادی ماڈل کلاس
Base = declarative_base()


# --- ڈیٹا بیس ماڈلز ---

class BaseMixin:
    """
    تمام ماڈلز کے لیے مشترکہ طریقے فراہم کرنے کے لیے ایک مکسن۔
    """
    def as_dict(self) -> Dict[str, Any]:
        """
        ماڈل آبجیکٹ کو ایک ڈکشنری میں تبدیل کرتا ہے، تاریخوں کو ISO فارمیٹ میں بدلتا ہے۔
        """
        d = {}
        for c in self.__table__.columns:
            value = getattr(self, c.name)
            if isinstance(value, datetime):
                d[c.name] = value.isoformat()
            else:
                d[c.name] = value
        return d

class ActiveSignal(Base, BaseMixin):
    """فعال ٹریڈنگ سگنلز کا ٹیبل۔"""
    __tablename__ = "active_signals"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String(128), unique=True, index=True, nullable=False, comment="منفرد سگنل شناخت کنندہ")
    symbol = Column(String(32), index=True, nullable=False, comment="ٹریڈنگ جوڑا، جیسے 'XAU/USD'")
    timeframe = Column(String(16), default="15min", comment="کینڈل کا ٹائم فریم")
    signal_type = Column(String(8), nullable=False, comment="'buy' یا 'sell'")
    entry_price = Column(Float, nullable=False, comment="سگنل کی انٹری قیمت")
    tp_price = Column(Float, nullable=False, comment="ٹیک پرافٹ کی قیمت")
    sl_price = Column(Float, nullable=False, comment="اسٹاپ لاس کی قیمت")
    confidence = Column(Float, comment="AI کا اعتماد کا اسکور (0-100)")
    reason = Column(String(1024), comment="سگنل کی AI کی تیار کردہ وجہ")
    component_scores = Column(JSON, nullable=True, comment="انفرادی حکمت عملی کے اجزاء کے اسکور")
    created_at = Column(DateTime, default=datetime.utcnow, comment="سگنل بننے کا وقت")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="آخری اپ ڈیٹ کا وقت")
    is_new = Column(Boolean, default=True, nullable=False, comment="کیا سگنل گریس پیریڈ میں ہے؟")

    def __repr__(self):
        return f"<ActiveSignal(id={self.id}, symbol='{self.symbol}', type='{self.signal_type}')>"

class CompletedTrade(Base, BaseMixin):
    """مکمل شدہ ٹریڈز کی تاریخ کا ٹیبل۔"""
    __tablename__ = "completed_trades"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String(128), unique=True, index=True, nullable=False)
    symbol = Column(String(32), index=True, nullable=False)
    timeframe = Column(String(16))
    signal_type = Column(String(8))
    entry_price = Column(Float)
    tp_price = Column(Float)
    sl_price = Column(Float)
    close_price = Column(Float, nullable=True, comment="ٹریڈ بند ہونے کی قیمت")
    reason_for_closure = Column(String(256), nullable=True, comment="ٹریڈ بند ہونے کی وجہ")
    outcome = Column(String(32), index=True, comment="'tp_hit', 'sl_hit', وغیرہ")
    confidence = Column(Float)
    reason = Column(String(1024))
    closed_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CompletedTrade(id={self.id}, symbol='{self.symbol}', outcome='{self.outcome}')>"

class FeedbackEntry(Base, BaseMixin):
    """مستقبل میں AI کو تربیت دینے کے لیے فیڈ بیک کا ٹیبل (فی الحال غیر فعال)۔"""
    __tablename__ = "feedback_entries"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(32), index=True)
    timeframe = Column(String(16))
    feedback = Column(String(256), comment="مثبت یا منفی فیڈ بیک")
    created_at = Column(DateTime, default=datetime.utcnow)

class CachedNews(Base, BaseMixin):
    """مارکیٹ کی خبروں کو کیش کرنے کے لیے ٹیبل۔"""
    __tablename__ = "cached_news"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)


def create_db_and_tables():
    """
    ڈیٹا بیس اور تمام بیان کردہ ٹیبلز بناتا ہے اگر وہ پہلے سے موجود نہ ہوں۔
    """
    try:
        logger.info("ڈیٹا بیس اور ٹیبلز کی حالت کی تصدیق کی جا رہی ہے...")
        Base.metadata.create_all(bind=engine)
        logger.info("ٹیبلز کامیابی سے بنائے یا تصدیق کیے گئے۔")
    except Exception as e:
        logger.error(f"ڈیٹا بیس بنانے میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        # یہاں سے باہر نکلنا یا دوبارہ کوشش کی منطق شامل کی جا سکتی ہے
        raise

