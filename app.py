import os
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from typing import Optional, Dict, Any

# --- ڈیٹا بیس کے لیے امپورٹس ---
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
# --- نئی تبدیلی: ماڈلز اور ٹیبل بنانے کا فنکشن امپورٹ کریں ---
from src.database.models import create_db_and_tables

# .env فائل سے ویری ایبلز لوڈ کریں
load_dotenv()

# --- ڈیٹا بیس کنکشن ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI ایپ کی شروعات
app = FastAPI(title="ScalpMaster AI API")

# --- پس منظر کے کاموں کے لیے شیڈیولر ---
scheduler = BackgroundScheduler()

# --- ہیلتھ چیک اینڈ پوائنٹ ---
@app.get("/health", status_code=200)
async def health_check():
    db_status = "ok"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError:
        db_status = "error"
    return {"status": "ok", "database_status": db_status}

# --- API اینڈ پوائنٹس (ابھی کے لیے سادہ) ---
@app.get("/api/live-signal", response_class=JSONResponse)
async def get_live_signal():
    return {"reason": "Database integration in progress..."}

@app.get("/api/history", response_class=JSONResponse)
async def get_history():
    return []

@app.get("/api/news", response_class=JSONResponse)
async def get_news():
    return {}

# --- ایپ کے شروع اور بند ہونے پر ایونٹس ---
@app.on_event("startup")
async def startup_event():
    print("--- ScalpMaster AI Server is starting up... ---")
    
    # --- نئی تبدیلی: ڈیٹا بیس میں ٹیبلز بنائیں ---
    create_db_and_tables()
    
    # ابھی کے لیے، ہم پس منظر کے کاموں کو شروع نہیں کر رہے
    # scheduler.start()
    print("--- Scheduler is paused during database setup. ---")

@app.on_event("shutdown")
async def shutdown_event():
    print("--- ScalpMaster AI Server is shutting down... ---")
    if scheduler.running:
        scheduler.shutdown()

# --- اسٹیٹک فائلیں اور روٹ پیج (سب سے آخر میں) ---
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
