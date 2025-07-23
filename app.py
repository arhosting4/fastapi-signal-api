import os
import asyncio
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from typing import List
from sqlalchemy.orm import Session

# Updated import paths based on folder structure
from src.database.models import create_db_and_tables, SessionLocal
import database_crud as crud
from signal_tracker import get_all_signals
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Load .env variables
load_dotenv()

# ✅ Create FastAPI app
app = FastAPI(title="ScalpMaster AI API")

# ✅ CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Background scheduler setup
scheduler = AsyncIOScheduler(timezone="UTC")

@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

@app.get("/api/live-signals", response_class=JSONResponse)
async def get_live_signals_api():
    """Return all active trade signals."""
    signals = get_all_signals()
    if not signals:
        return {"message": "AI is actively scanning the markets... No high-confidence signals at the moment."}
    return signals

@app.get("/api/history", response_class=JSONResponse)
async def get_history(db: Session = Depends(get_db)):
    try:
        trades = crud.get_completed_trades(db)
        return trades
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/api/news", response_class=JSONResponse)
async def get_news(db: Session = Depends(get_db)):
    try:
        news = crud.get_cached_news(db)
        if not news:
            return {"message": "No high-impact news found."}
        return news
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")

# ✅ Start scheduler and DB at startup
@app.on_event("startup")
async def startup_event():
    create_db_and_tables()

    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=5), id="hunt_for_signals")
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), id="check_active_signals")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="update_news")

    try:
        scheduler.start()
        logger.info("Scheduler started.")
    except Exception as e:
        logger.error(f"Scheduler failed to start: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    try:
        scheduler.shutdown()
        logger.info("Scheduler shutdown successfully.")
    except Exception as e:
        logger.warning(f"Scheduler shutdown failed: {e}")

# ✅ Serve static frontend files
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
