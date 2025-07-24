# filename: app.py

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

# .env فائل سے متغیرات لوڈ کریں
load_dotenv()

# لاگنگ سیٹ اپ
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - [%(module)s] - %(message)s")
logger = logging.getLogger(__name__)

# FastAPI ایپ بنائیں
app = FastAPI(title="ScalpMaster AI API", version="1.2.1") # ورژن اپ ڈیٹ کیا گیا

# CORS مڈل ویئر
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- API روٹس جو پہلے api_routes.py میں تھے ---

def get_db():
    """ڈیٹا بیس سیشن فراہم کرتا ہے۔"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health", status_code=200, tags=["System"])
async def health_check():
    """سروس کی صحت کی جانچ کرتا ہے۔"""
    return {"status": "ok", "version": app.version}

@app.get("/api/live-signals", tags=["Trading"])
async def get_live_signals_api():
    """تمام فعال تجارتی سگنلز واپس کرتا ہے۔"""
    signals = get_all_signals()
    if not signals:
        return {"message": "AI مارکیٹ کو اسکین کر رہا ہے... اس وقت کوئی اعلیٰ اعتماد والا سگنل نہیں ہے۔"}
    return signals

@app.get("/api/history", tags=["Trading"])
async def get_history(db: Session = Depends(get_db)):
    """مکمل شدہ تجارت کی تاریخ واپس کرتا ہے۔"""
    try:
        return crud.get_completed_trades(db)
    except Exception as e:
        logger.error(f"تاریخ حاصل کرنے میں خرابی: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="اندرونی سرور کی خرابی۔")

@app.get("/api/news", tags=["Market Data"])
async def get_news(db: Session = Depends(get_db)):
    """کیش شدہ مارکیٹ کی خبریں واپس کرتا ہے۔"""
    try:
        news = crud.get_cached_news(db)
        return news or {"articles": []}
    except Exception as e:
        logger.error(f"خبریں حاصل کرنے میں خرابی: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="اندرونی سرور کی خرابی۔")

# --- شیڈیولر سیٹ اپ ---
scheduler = AsyncIOScheduler(timezone="UTC")
scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=config.HUNT_JOB_MINUTES), id="hunt_for_signals")
scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=config.CHECK_JOB_MINUTES), id="check_active_signals")
scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=config.NEWS_JOB_HOURS), id="update_news")

@app.on_event("startup")
async def startup_event():
    """ایپلیکیشن اسٹارٹ اپ پر چلتا ہے۔"""
    logger.info("FastAPI ورکر شروع ہو رہا ہے...")
    create_db_and_tables()
    logger.info("ڈیٹا بیس ٹیبلز کی تصدیق ہو گئی۔")

@app.on_event("shutdown")
async def shutdown_event():
    """ایپلیکیشن بند ہونے پر چلتا ہے۔"""
    logger.info("FastAPI ورکر بند ہو رہا ہے۔")

# فرنٹ اینڈ فائلوں کو پیش کریں
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
