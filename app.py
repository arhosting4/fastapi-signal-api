# filename: app.py
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import config
from models import create_db_and_tables
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
from api_routes import router as api_router

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - [%(module)s] - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="ScalpMaster AI API", version="1.2.0") # ورژن اپ ڈیٹ کیا گیا

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# شیڈیولر سیٹ اپ (اسے یہاں شروع نہیں کریں گے)
scheduler = AsyncIOScheduler(timezone="UTC")
scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=config.HUNT_JOB_MINUTES), id="hunt_for_signals")
scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=config.CHECK_JOB_MINUTES), id="check_active_signals")
scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=config.NEWS_JOB_HOURS), id="update_news")

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI ورکر شروع ہو رہا ہے...")
    create_db_and_tables()
    logger.info("ڈیٹا بیس ٹیبلز کی تصدیق ہو گئی۔")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FastAPI ورکر بند ہو رہا ہے۔")

# API روٹس کو شامل کریں
app.include_router(api_router)

# فرنٹ اینڈ پیش کریں
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
