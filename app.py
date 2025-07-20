# filename: app.py

import os
import asyncio
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from typing import List
from sqlalchemy.orm import Session

from src.database.models import create_db_and_tables, SessionLocal
import database_crud as crud
# --- اہم اصلاح: signal_tracker سے درست فنکشنز امپورٹ کیے گئے ---
from signal_tracker import get_all_signals
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache

load_dotenv()
app = FastAPI(title="ScalpMaster AI API")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

scheduler = AsyncIOScheduler(timezone="UTC")

@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

@app.get("/api/live-signals", response_class=JSONResponse)
async def get_live_signals_api():
    """تمام فعال سگنلز کی فہرست لوٹاتا ہے۔"""
    signals = get_all_signals()
    if not signals:
        return {"message": "AI is actively scanning the markets... No high-confidence signals at the moment."}
    return signals

@app.get("/api/history", response_class=JSONResponse)
async def get_history(db: Session = Depends(get_db)):
    try:
        trades = crud.get_completed_trades(db, limit=100)
        return [
            {
                "symbol": trade.symbol, "timeframe": trade.timeframe,
                "signal_type": trade.signal_type, "entry_price": trade.entry_price,
                "outcome": trade.outcome, "closed_at": trade.closed_at.strftime("%Y-%m-%d %H:%M:%S")
            } for trade in trades
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Could not fetch trade history.")

@app.get("/api/news", response_class=JSONResponse)
async def get_news(db: Session = Depends(get_db)):
    try:
        news_items = crud.get_cached_news(db)
        if not news_items:
            return {"status": "All Clear", "reason": "No upcoming high-impact news events found in the cache."}
        return news_items
    except Exception as e:
        raise HTTPException(status_code=500, detail="Could not fetch news.")

@app.on_event("startup")
async def startup_event():
    print("--- ScalpMaster AI Server is starting up... ---")
    create_db_and_tables()
    
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=5), id="hunter_job", name="Signal Hunter")
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), id="feedback_job", name="Feedback Checker")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="news_job", name="News Updater")
    
    scheduler.start()
    await asyncio.sleep(2)
    # UTC ٹائم زون کے ساتھ next_run_time سیٹ کریں
    scheduler.get_job("news_job").modify(next_run_time=datetime.now(scheduler.timezone))
    await asyncio.sleep(2)
    scheduler.get_job("hunter_job").modify(next_run_time=datetime.now(scheduler.timezone))
    
    print("--- Scheduler started with all jobs. ---")

@app.on_event("shutdown")
async def shutdown_event():
    if scheduler.running:
        scheduler.shutdown()
    print("--- ScalpMaster AI Server is shutting down. ---")

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
