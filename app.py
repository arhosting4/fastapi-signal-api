# app.py

import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from contextlib import asynccontextmanager
from typing import List, Dict, Any

# --- مقامی امپورٹس ---
from src.database.config import SessionLocal, engine
from src.database.models import create_db_and_tables
import database_crud as crud
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
# --- اہم تبدیلی: signal_tracker سے نئے فنکشنز امپورٹ کریں ---
from signal_tracker import get_active_signals

# --- شیڈولر آبجیکٹ ---
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- ایپ کے آغاز پر چلنے والا کوڈ ---
    print("--- Application Startup ---")
    create_db_and_tables()
    
    # --- پس منظر کے کاموں کو شیڈول کریں ---
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=5), args=[SessionLocal], misfire_grace_time=60)
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), args=[SessionLocal], misfire_grace_time=30)
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=6), misfire_grace_time=300)
    scheduler.start()
    print("--- Scheduler Started ---")
    yield
    # --- ایپ کے بند ہونے پر چلنے والا کوڈ ---
    print("--- Application Shutdown ---")
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# --- API اینڈ پوائنٹس ---

@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

# --- اہم تبدیلی: اینڈ پوائنٹ کا نام اور واپسی کی قسم ---
@app.get("/api/active-signals", response_model=List[Dict[str, Any]])
async def get_live_signals_endpoint():
    """
    تمام فعال، اعلیٰ معیار کے سگنلز کی فہرست واپس کرتا ہے۔
    """
    signals = get_active_signals()
    if not signals:
        # اگر کوئی سگنل نہیں ہے تو خالی فہرست واپس کریں، یہ ایرر نہیں ہے
        return []
    return signals

@app.get("/api/completed-trades")
async def get_completed_trades_endpoint():
    db = SessionLocal()
    try:
        trades = crud.get_completed_trades_from_db(db, limit=50)
        return trades
    finally:
        db.close()

@app.get("/api/news")
async def get_news_endpoint():
    news = crud.get_news_from_cache()
    if not news:
        raise HTTPException(status_code=404, detail="Could not load news events. The server might be initializing.")
    return news

# --- اسٹیٹک فائلیں ---
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
