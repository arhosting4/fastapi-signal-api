# filename: app.py
import os
import asyncio
import logging
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

# مقامی امپورٹس
import config
import database_crud as crud
from models import create_db_and_tables, SessionLocal
from signal_tracker import get_all_signals
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache

# .env متغیرات لوڈ کریں
load_dotenv()

# لاگنگ کو بہتر بنائیں
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(module)s] - %(message)s",
)
logger = logging.getLogger(__name__)

# FastAPI ایپ بنائیں
app = FastAPI(title="ScalpMaster AI API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB انحصار
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# شیڈیولر سیٹ اپ
scheduler = AsyncIOScheduler(timezone="UTC")

@app.get("/health", status_code=200, tags=["System"])
async def health_check():
    """سسٹم کی صحت کی جانچ کریں"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/live-signals", response_class=JSONResponse, tags=["Trading"])
async def get_live_signals_api():
    """تمام فعال تجارتی سگنلز واپس کرتا ہے"""
    signals = get_all_signals()
    if not signals:
        return JSONResponse(
            status_code=200,
            content={"message": "AI مارکیٹ کو اسکین کر رہا ہے... اس وقت کوئی اعلیٰ اعتماد والا سگنل نہیں ہے۔"}
        )
    return signals

@app.get("/api/history", response_class=JSONResponse, tags=["Trading"])
async def get_history(db: Session = Depends(get_db)):
    """مکمل شدہ ٹریڈز کی تاریخ واپس کرتا ہے"""
    try:
        trades = crud.get_completed_trades(db)
        return trades
    except Exception as e:
        logger.error(f"تاریخ حاصل کرنے میں خرابی: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="اندرونی سرور کی خرابی۔")

@app.get("/api/news", response_class=JSONResponse, tags=["Market Data"])
async def get_news(db: Session = Depends(get_db)):
    """کیش شدہ مارکیٹ کی خبریں واپس کرتا ہے"""
    try:
        news = crud.get_cached_news(db)
        if not news:
            return JSONResponse(
                status_code=200,
                content={"message": "کوئی اعلیٰ اثر والی خبر نہیں ملی۔"}
            )
        return news
    except Exception as e:
        logger.error(f"خبریں حاصل کرنے میں خرابی: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="اندرونی سرور کی خرابی۔")

@app.on_event("startup")
async def startup_event():
    """ایپلیکیشن اسٹارٹ اپ پر چلتا ہے"""
    logger.info("ScalpMaster AI API شروع ہو رہا ہے...")
    create_db_and_tables()
    logger.info("ڈیٹا بیس ٹیبلز کی تصدیق ہو گئی۔")

    # پس منظر کے کاموں کو شیڈول کریں
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=config.HUNT_JOB_MINUTES), id="hunt_for_signals")
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=config.CHECK_JOB_MINUTES), id="check_active_signals")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=config.NEWS_JOB_HOURS), id="update_news")

    try:
        scheduler.start()
        logger.info("شیڈیولر کامیابی سے شروع ہو گیا۔")
    except Exception as e:
        logger.error(f"شیڈیولر شروع کرنے میں ناکام: {e}", exc_info=True)

@app.on_event("shutdown")
async def shutdown_event():
    """ایپلیکیشن بند ہونے پر چلتا ہے"""
    try:
        scheduler.shutdown()
        logger.info("شیڈیولر کامیابی سے بند ہو گیا۔")
    except Exception as e:
        logger.warning(f"شیڈیولر بند کرنے میں ناکام: {e}")

# فرنٹ اینڈ پیش کریں
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
    
