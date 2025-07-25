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

import config
import database_crud as crud
from models import create_db_and_tables, SessionLocal
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
from signal_tracker import get_all_signals

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - [%(module)s] - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="ScalpMaster AI API", version="1.4.0") # ورژن اپ ڈیٹ کیا گیا
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- شیڈیولر سیٹ اپ ---
scheduler = AsyncIOScheduler(timezone="UTC")
scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=config.HUNT_JOB_MINUTES), id="hunt_for_signals")
scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=config.CHECK_JOB_MINUTES), id="check_active_signals")
scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=config.NEWS_JOB_HOURS), id="update_news")

def start_scheduler_safely():
    """ریس کنڈیشن سے بچنے کے لیے فائل لاک کا استعمال کرتے ہوئے شیڈیولر شروع کرتا ہے۔"""
    lock_file_path = "/tmp/scheduler_lock"
    try:
        # لاک حاصل کرنے کی کوشش کریں
        fd = os.open(lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        # --- لاک حاصل ہو گیا، اب شیڈیولر شروع کریں ---
        try:
            if not scheduler.running:
                scheduler.start()
                logger.info("★★★ شیڈیولر کامیابی سے شروع ہو گیا۔ ★★★")
        finally:
            # لاک کو بند کریں (اسے ہٹائیں نہیں تاکہ دوسرے ورکرز اسے دوبارہ شروع نہ کریں)
            os.close(fd)
    except FileExistsError:
        logger.info("شیڈیولر پہلے ہی کسی دوسرے ورکر کے ذریعے شروع کیا جا چکا ہے۔")
    except Exception as e:
        logger.error(f"شیڈیولر شروع کرنے میں ناکام: {e}", exc_info=True)
        # اگر خرابی ہو تو لاک فائل کو ہٹا دیں تاکہ اگلی بار کوشش کی جا سکے
        if os.path.exists(lock_file_path):
            os.remove(lock_file_path)

@app.on_event("startup")
async def startup_event():
    """ایپلیکیشن اسٹارٹ اپ پر چلتا ہے۔"""
    logger.info("FastAPI ورکر شروع ہو رہا ہے...")
    create_db_and_tables()
    logger.info("ڈیٹا بیس کی حالت کی تصدیق ہو گئی۔")
    # محفوظ طریقے سے شیڈیولر شروع کریں
    start_scheduler_safely()

@app.on_event("shutdown")
async def shutdown_event():
    """ایپلیکیشن بند ہونے پر چلتا ہے۔"""
    logger.info("FastAPI ورکر بند ہو رہا ہے۔")
    if scheduler.running:
        scheduler.shutdown()
        logger.info("شیڈیولر بند ہو گیا۔")
    # شٹ ڈاؤن پر لاک فائل کو صاف کریں
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

# ... (باقی تمام API روٹس ویسے ہی رہیں گے) ...

# فرنٹ اینڈ پیش کریں
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
