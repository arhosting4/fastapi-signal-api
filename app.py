# filename: app.py

import asyncio
import logging
import time # ★★★ نیا امپورٹ ★★★
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, create_db_and_tables
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
from websocket_manager import manager
from price_stream import start_price_websocket, get_last_heartbeat # ★★★ نیا امپورٹ ★★★

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="ScalpMaster AI API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# ★★★ نیا: ہمارا نگران کام ★★★
async def price_stream_watchdog():
    """
    یہ چیک کرتا ہے کہ آیا قیمتوں کا سلسلہ زندہ ہے یا نہیں۔
    """
    last_beat = get_last_heartbeat()
    # اگر 5 منٹ (300 سیکنڈ) سے کوئی دل کی دھڑکن نہیں ہے
    if time.time() - last_beat > 300:
        logger.critical("!!! خطرہ: پرائس سٹریم پچھلے 5 منٹ سے خاموش ہے۔ سسٹم پھنس سکتا ہے۔ براہ کرم سرور کو دوبارہ شروع کریں!!!")

# ... (باقی API روٹس ویسے ہی رہیں گے) ...
@app.get("/health", status_code=200)
async def health_check(): return {"status": "ok"}
# ... (دیگر روٹس) ...

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI ورکر شروع ہو رہا ہے...")
    asyncio.create_task(start_price_websocket())
    create_db_and_tables()
    await update_economic_calendar_cache()
    
    if not hasattr(app.state, "scheduler") or not app.state.scheduler.running:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        
        scheduler = AsyncIOScheduler(timezone="UTC")
        scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=5), id="hunt_for_signals")
        scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), id="check_active_signals")
        scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="update_news")
        # ★★★ اہم: نگران کو شیڈیولر میں شامل کریں ★★★
        scheduler.add_job(price_stream_watchdog, IntervalTrigger(minutes=1), id="price_stream_watchdog")
        
        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("★★★ شیڈیولر اور نگران کامیابی سے شروع ہو گئے۔ ★★★")
    else:
        logger.info("شیڈیولر پہلے ہی کسی دوسرے ورکر کے ذریعے شروع کیا جا چکا ہے۔")

# ... (باقی کوڈ ویسا ہی رہے گا) ...
