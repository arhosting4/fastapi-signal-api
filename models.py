from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import os

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
Base = declarative_base()

class ActiveTrade(Base):
    __tablename__ = 'active_trades'
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    signal = Column(String)
    timeframe = Column(String)
    entry_price = Column(Float)
    tp = Column(Float)
    sl = Column(Float)
    confidence = Column(Float)
    reason = Column(String)
    tier = Column(String)
    entry_time = Column(DateTime(timezone=True), server_default=func.now())

class CompletedTrade(Base):
    __tablename__ = 'completed_trades'
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    signal = Column(String)
    entry_price = Column(Float)
    close_price = Column(Float)
    tp = Column(Float)
    sl = Column(Float)
    outcome = Column(String)
    entry_time = Column(DateTime)
    close_time = Column(DateTime(timezone=True), server_default=func.now())

def create_db_and_tables():
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("--- Database tables recreated with correct schema. ---")
    except Exception as e:
        print(f"--- ERROR creating database tables: {e} ---")
        try:
            Base.metadata.create_all(bind=engine)
            print("--- Database tables created (fallback method). ---")
        except Exception as e2:
            print(f"--- CRITICAL ERROR: Could not create database tables: {e2} ---")
            
