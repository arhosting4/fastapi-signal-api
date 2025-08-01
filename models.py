# filename: models.py

import os
import logging
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    DateTime, JSON, Boolean, func
)
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
from datetime import datetime

# ------------------------------------------------------------------------------
# 📦 .env فائل سے ماحولیاتی متغیرات لوڈ کریں
# ------------------------------------------------------------------------------
load_dotenv()
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# 🔌 ڈیٹا بیس کنکشن سیٹ اپ کریں
# ------------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./signals.db")

# PostgreSQL compatibility fix
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# اگر SQLite نہیں ہے تو advanced engine args لگائیں
engine_args = {}
if not DATABASE_URL.startswith("sqlite"):
    engine_args = {
        "pool_size": 10,
        "max_overflow": 2,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

# 🔧 انجن بنائیں
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    **engine_args
)

# 📦 سیشن اور بیس ماڈل سیٹ کریں
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ------------------------------------------------------------------------------
# 📊 سگنلز کا مرکزی ماڈل
# ------------------------------------------------------------------------------
class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)  # کرنسی یا جوڑا جیسے BTC/USD
    signal_type = Column(String, nullable=False)  # BUY یا SELL
    price = Column(Float, nullable=False)  # انٹری قیمت
    tp = Column(Float, nullable=True)  # ٹیک پرافٹ
    sl = Column(Float, nullable=True)  # اسٹاپ لاس
    status = Column(String, default="active")  # active, hit_tp, hit_sl, expired
    confidence = Column(Float, default=0.0)  # AI اعتماد فیصد
    tier = Column(String, default="N/A")  # سگنل کا درجہ
    reason = Column(String, default="N/A")  # AI نے سگنل کیوں دیا
    additional_data = Column(JSON, default={})  # کوئی اضافی انفارمیشن (جیسے indicators)
    created_at = Column(DateTime, default=func.now())  # سگنل کب بنایا گیا
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_manual = Column(Boolean, default=False)  # AI vs human generated?

# ------------------------------------------------------------------------------
# 🧪 مزید ٹیبلز نیچے define کیے جا سکتے ہیں اگر درکار ہوں
# ------------------------------------------------------------------------------

# اگر پہلی بار DB structure setup کرنا ہو:
# Base.metadata.create_all(bind=engine)
