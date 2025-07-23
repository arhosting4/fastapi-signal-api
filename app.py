# filename: app.py

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
from pydantic import BaseModel

from src.database.models import create_db_and_tables, SessionLocal
import database_crud as crud
from signal_tracker import get_all_signals
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# FastAPI app
app = FastAPI(title="ScalpMaster AI API")

# Allow CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace * with frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Scheduler
scheduler = AsyncIOScheduler(timezone="UTC")

# Health check
@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

# Live Signals API
@app.get("/api/live-signals", response_class=JSONResponse)
async def get_live_signals_api():
    signals = get_all_signals()
    if not signals:
        return {"message": "AI is actively scanning the markets... No high-confidence signals at the moment."}
    return signals

# History API
@app.get("/api/history", response_class=JSONResponse)
async def get_history(db: Session = Depends(get_db)):
    try:
        trades = crud.get_completed_trades(db)
        return trades
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")

# News API
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

# ✅ Feedback Model
class FeedbackIn(BaseModel):
    symbol: str
    timeframe: str
    feedback: str

# ✅ Feedback API
@app.post("/api/feedback", response_class=JSONResponse)
async def submit_feedback(feedback: FeedbackIn, db: Session = Depends(get_db)):
    try:
        saved = crud.add_feedback_entry(
            db=db,
            symbol=feedback.symbol,
            timeframe=feedback.timeframe,
            feedback=feedback.feedback
        )
        return {"message": "Feedback saved", "id": saved.id}
    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to store feedback")

# Startup: Create DB + Schedule jobs
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

# Shutdown
@app.on_event("shutdown")
async def shutdown_event():
    try:
        scheduler.shutdown()
        logger.info("Scheduler shutdown successfully.")
    except Exception as e:
        logger.warning(f"Scheduler shutdown failed: {e}")

# ✅ Serve Static Frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
