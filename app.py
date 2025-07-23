# filename: app.py

import os
import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from src.database.models import create_db_and_tables, SessionLocal
import database_crud as crud
from utils.signal_tracker import get_all_signals
from utils.hunter import hunt_for_signals_job
from utils.feedback_checker import check_active_signals_job
from utils.sentinel import update_economic_calendar_cache

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env
load_dotenv()

# FastAPI instance
app = FastAPI(title="ScalpMaster AI API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use your frontend domain here in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency for DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Health check
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# API: Live Signals
@app.get("/api/live-signals", response_class=JSONResponse)
async def get_live_signals_api():
    signals = get_all_signals()
    if not signals:
        return {"message": "AI is scanning... No high-confidence signals."}
    return signals

# API: History
@app.get("/api/history", response_class=JSONResponse)
async def get_history(db: Session = Depends(get_db)):
    try:
        return crud.get_completed_trades(db)
    except Exception as e:
        logger.error(f"History error: {e}")
        raise HTTPException(status_code=500, detail="Error fetching history.")

# API: News
@app.get("/api/news", response_class=JSONResponse)
async def get_news(db: Session = Depends(get_db)):
    try:
        news = crud.get_cached_news(db)
        return news or {"message": "No news available."}
    except Exception as e:
        logger.error(f"News error: {e}")
        raise HTTPException(status_code=500, detail="Error fetching news.")

# Scheduler
scheduler = AsyncIOScheduler(timezone="UTC")

@app.on_event("startup")
async def on_startup():
    create_db_and_tables()

    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=5), id="hunt_signals")
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), id="check_feedback")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="update_news")

    try:
        scheduler.start()
        logger.info("Scheduler started")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")

@app.on_event("shutdown")
async def on_shutdown():
    try:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
    except Exception as e:
        logger.warning(f"Scheduler shutdown error: {e}")

# Serve static frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
