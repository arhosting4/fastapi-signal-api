import os
import asyncio
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from typing import List, Optional

from sqlalchemy.orm import Session
from src.database.models import create_db_and_tables, SessionLocal
import database_crud as crud
from signal_tracker import get_live_signal as get_cached_signal

# --- ہمارے پس منظر کے کام ---
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

scheduler = BackgroundScheduler()

@app.get("/health", status_code=200)
async def health_check(db: Session = Depends(get_db)):
    db_status = "ok"
    try:
        crud.get_completed_trades(db, limit=1) 
    except Exception:
        db_status = "error"
    return {"status": "ok", "database_status": db_status}

@app.get("/api/live-signal", response_class=JSONResponse)
async def get_live_signal_api():
    signal = get_cached_signal()
    if not signal:
        return {"reason": "AI is actively scanning the markets..."}
    return signal

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
        return news_items
    except Exception as e:
        raise HTTPException(status_code=500, detail="Could not fetch news.")

@app.on_event("startup")
async def startup_event():
    print("--- ScalpMaster AI Server is starting up... ---")
    create_db_and_tables()
    
    # --- پس منظر کے کاموں کو دوبارہ شروع کریں ---
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(seconds=30), id="hunter_job", name="Signal Hunter")
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), id="feedback_job", name="Feedback Checker")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="news_job", name="News Updater")
    
    # فوری طور پر ایک بار چلائیں تاکہ ایپ شروع ہوتے ہی ڈیٹا دستیاب ہو
    await asyncio.sleep(2) # ایپ کو مکمل طور پر شروع ہونے دیں
    scheduler.get_job("news_job").modify(next_run_time=datetime.now())
    scheduler.get_job("hunter_job").modify(next_run_time=datetime.now())
    
    scheduler.start()
    print("--- Scheduler started with all jobs. ---")

@app.on_event("shutdown")
async def shutdown_event():
    print("--- ScalpMaster AI Server is shutting down... ---")
    if scheduler.running:
        scheduler.shutdown()

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
