# filename: database_config.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Render.com خود بخود DATABASE_URL فراہم کرتا ہے جب آپ ڈیٹا بیس منسلک کرتے ہیں۔
# اگر ہم مقامی طور پر چلا رہے ہیں، تو ہم ایک SQLite فائل استعمال کریں گے۔
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/local_database.db")

# اس بات کو یقینی بنانا کہ اگر ہم SQLite استعمال کر رہے ہیں تو 'data' فولڈر موجود ہو۔
if DATABASE_URL.startswith("sqlite"):
    os.makedirs("data", exist_ok=True)
    # SQLite کے لیے خصوصی کنکشن آرگیومنٹس
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL (Render پر) کے لیے
    engine = create_engine(DATABASE_URL)

# ڈیٹا بیس سیشن بنانے کے لیے ایک فیکٹری
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ماڈلز کے لیے بنیادی کلاس
Base = declarative_base()
