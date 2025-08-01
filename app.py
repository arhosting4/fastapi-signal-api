# filename: app.py

import asyncio
import logging
import os
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, create_db_and_tables, engine
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
from websocket_manager import manager
from key_manager import key_manager

# ★★★ LOGGER CONFIGURATION ★★★
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [APP] - %(message)s"
)
logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ★★★ FASTAPI INSTANCE ★★★
app = FastAPI(title="ScalpMaster AI API")

# CORS CONFIGURATION
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ★★★ STATIC FILES ★★★
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

# DB SESSION DEPENDENCY
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ROUTES ---
@app.get("/api/active-signals", response_class=JSONResponse)
async def get_active_signals(db: Session = Depends(get_db)):
    try:
        signals = crud.get_all_active_signals_from_db(db)
        return [s.as_dict() for s in signals]
    except Exception as e:
        logger.error(f"[APP] فعال سگنلز حاصل کرنے میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

@app.get("/api/daily-stats", response_class=JSONResponse)
async def get_daily_stats_endpoint(db: Session = Depends(get_db)):
    try:
        stats = crud.get_daily_stats(db)
        return stats
    except Exception as e:
        logger.error(f"[APP] روزانہ کے اعداد و شمار حاصل کرنے میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

# --- BACKGROUND TASKS INITIALIZATION ---
async def start_background_tasks():
    """
    پس منظر کے کاموں کو محفوظ طریقے سے شروع کرتا ہے۔
    یہ مستقبل میں multi-worker aware ہو سکتا ہے۔
    """
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        logger.info("[APP] شیڈیولر پہلے سے فعال ہے۔")
        return

    logger.info("[APP] >>> پس منظر کے کام شروع ہو رہے ہیں...")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=3))
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=4))
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(minutes=15))

    scheduler.start()
    app.state.scheduler = scheduler

# APP STARTUP EVENT
@app.on_event("startup")
async def on_startup():
    create_db_and_tables()
    await start_background_tasks()
