# filename: app.py

import os
import asyncio
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
# --- اہم اور حتمی اصلاح: BackgroundScheduler کی بجائے AsyncIOScheduler کا استعمال کریں ---
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from typing import List
from sqlalchemy.orm import Session

# ہمارے پروجیکٹ کے ماڈیولز
from src.database.models import create_db_and_tables, SessionLocal
import database_crud as crud
from signal_tracker import get_live_signals
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache

load_dotenv()
app = FastAPI(title="ScalpMaster AI API - Multi-Signal Edition")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- تبدیلی: AsyncIOScheduler کا استعمال ---
scheduler = AsyncIOScheduler(timezone="UTC")

@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok", "mode": "multi-signal"}

@app.get("/api/live-signals", response_class=JSONResponse)
async def get_live_signals_api():
    signals = get_live_signals()
    if not signals:
        return JSONResponse(
            content={"message": "AI is actively scanning the markets. No high-confidence signals at the moment."},
            status_code=200
        )
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
    # ڈیٹا بیس ٹیبلز کو یقینی بنائیں
    create_db_and_tables()
    
    # تمام جابز کو شیڈول کریں
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=5), id="hunter_job", name="Signal Hunter")
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), id="feedback_job", name="Feedback Checker")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="news_job", name="News Updater")
    
    # پہلی بار چلانے کے لیے جابز کو فوری طور پر ٹریگر کریں
    scheduler.get_job("news_job").modify(next_run_time=datetime.now(scheduler.timezone))
    scheduler.get_job("hunter_job").modify(next_run_time=datetime.now(scheduler.timezone))
    
    # شیڈولر کو شروع کریں
    if not scheduler.running:
        scheduler.start()
        print("--- Scheduler started with all jobs. ---")

@app.on_event("shutdown")
async def shutdown_event():
    if scheduler.running:
        scheduler.shutdown()
    print("--- ScalpMaster AI Server is shutting down. ---")

# فرنٹ اینڈ فائلوں کو پیش کرنے کے لیے
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
