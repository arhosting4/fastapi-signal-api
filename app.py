import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from contextlib import asynccontextmanager
from typing import List, Dict, Any

# --- مقامی امپورٹس (فلیٹ ڈھانچے کے مطابق) ---
from database_config import SessionLocal
from database_models import create_db_and_tables
import database_crud as crud
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
from signal_tracker import get_active_signals

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- Application Startup ---")
    create_db_and_tables()
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=5), args=[SessionLocal], misfire_grace_time=60)
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), args=[SessionLocal], misfire_grace_time=30)
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=6), misfire_grace_time=300)
    scheduler.start()
    print("--- Scheduler Started ---")
    yield
    print("--- Application Shutdown ---")
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

@app.get("/api/active-signals", response_model=List[Dict[str, Any]])
async def get_live_signals_endpoint():
    signals = get_active_signals()
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
        raise HTTPException(status_code=404, detail="Could not load news events.")
    return news

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
