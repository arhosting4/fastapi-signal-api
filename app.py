# filename: app.py

import os
import time
import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

# اب config.py پر کوئی انحصار نہیں
# import config 
import database_crud as crud
from models import create_db_and_tables, SessionLocal
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
from signal_tracker import get_all_signals

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - [%(module)s] - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="ScalpMaster AI API", version="2.0.0-stable") # حتمی ورژن
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ==============================================================================
# شیڈیولر کے وقفے براہ راست یہاں شامل کر دیے گئے ہیں
# ==============================================================================
HUNT_JOB_MINUTES = 5
CHECK_JOB_MINUTES = 1
NEWS_JOB_HOURS = 4
# ==============================================================================

scheduler = AsyncIOScheduler(timezone="UTC")
scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=HUNT_JOB_MINUTES), id="hunt_for_signals")
scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=CHECK_JOB_MINUTES), id="check_active_signals")
scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=NEWS_JOB_HOURS), id="update_news")

def start_scheduler_safely():
    lock_file_path = "/tmp/scheduler_lock"
    try:
        fd = os.open(lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            if not scheduler.running:
                scheduler.start()
                logger.info("★★★ شیڈیولر کامیابی سے شروع ہو گیا۔ ★★★")
        finally:
            os.close(fd)
    except FileExistsError:
        logger.info("شیڈیولر پہلے ہی کسی دوسرے ورکر کے ذریعے شروع کیا جا چکا ہے۔")
    except Exception as e:
        logger.error(f"شیڈیولر شروع کرنے میں ناکام: {e}", exc_info=True)
        if os.path.exists(lock_file_path):
            os.remove(lock_file_path)

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI ورکر شروع ہو رہا ہے...")
    create_db_and_tables()
    logger.info("ڈیٹا بیس کی حالت کی تصدیق ہو گئی۔")
    start_scheduler_safely()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FastAPI ورکر بند ہو رہا ہے۔")
    if scheduler.running:
        scheduler.shutdown()
        logger.info("شیڈیولر بند ہو گیا۔")
    lock_file_path = "/tmp/scheduler_lock"
    if os.path.exists(lock_file_path):
        os.remove(lock_file_path)

# --- API روٹس ---
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.get("/health", status_code=200, tags=["System"])
async def health_check():
    return {"status": "ok", "version": app.version, "scheduler_running": scheduler.running}

@app.get("/api/live-signals", tags=["Trading"])
async def get_live_signals_api():
    signals = get_all_signals()
    return signals if signals else []

@app.get("/api/history", tags=["Trading"])
async def get_history(db: Session = Depends(get_db)):
    try:
        return crud.get_completed_trades(db)
    except Exception as e:
        logger.error(f"تاریخ حاصل کرنے میں خرابی: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="اندرونی سرور کی خرابی۔")

@app.get("/api/news", tags=["Market Data"])
async def get_news(db: Session = Depends(get_db)):
    try:
        news = crud.get_cached_news(db)
        return news or {"articles": []}
    except Exception as e:
        logger.error(f"خبریں حاصل کرنے میں خرابی: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="اندرونی سرور کی خرابی۔")

# فرنٹ اینڈ پیش کریں
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
    
