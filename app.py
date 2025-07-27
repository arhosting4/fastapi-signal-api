# filename: app.py

import asyncio
import logging
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, create_db_and_tables
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job # price_stream_logic کو یہاں سے ہٹا دیا گیا ہے
from sentinel import update_economic_calendar_cache
from websocket_manager import manager

# ==============================================================================
# ★★★ لاگنگ کا حتمی اور مکمل کنٹرول ★★★
# ==============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
# ==============================================================================

# FastAPI ایپ
app = FastAPI(title="ScalpMaster AI API")

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

async def start_background_tasks():
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        logger.info("پس منظر کے کام پہلے ہی چل رہے ہیں۔")
        return

    logger.info(">>> پس منظر کے تمام کام شروع ہو رہے ہیں...")
    
    scheduler = AsyncIOScheduler(timezone="UTC")
    
    def system_heartbeat_job():
        logger.info("❤️ سسٹم ہارٹ بیٹ: شیڈیولر زندہ ہے اور پس منظر کے کام فعال ہیں۔")

    scheduler.add_job(system_heartbeat_job, IntervalTrigger(minutes=5), id="system_heartbeat")
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=5), id="hunt_for_signals")
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), id="check_active_signals")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="update_news")
    
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("★★★ شیڈیولر کامیابی سے شروع ہو گیا۔ ★★★")

    # WebSocket پرائس سٹریم کو غیر فعال کر دیا گیا ہے
    logger.info("پرائس سٹریم غیر فعال ہے۔ قیمتیں ہر منٹ REST API کے ذریعے حاصل کی جائیں گی۔")

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI سرور شروع ہو رہا ہے...")
    create_db_and_tables()
    logger.info("ڈیٹا بیس کی حالت کی تصدیق ہو گئی۔")
    asyncio.create_task(start_background_tasks())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FastAPI سرور بند ہو رہا ہے۔")
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        app.state.scheduler.shutdown()
        logger.info("شیڈیولر کامیابی سے بند ہو گیا۔")

@app.websocket("/ws/live-signals")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("کلائنٹ نے WebSocket کنکشن بند کر دیا۔")

@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

@app.get("/api/history", response_class=JSONResponse)
async def get_history(db: Session = Depends(get_db)):
    try:
        trades = crud.get_completed_trades(db)
        return trades
    except Exception as e:
        logger.error(f"ہسٹری حاصل کرنے میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

@app.get("/api/news", response_class=JSONResponse)
async def get_news(db: Session = Depends(get_db)):
    try:
        news = crud.get_cached_news(db)
        return news
    except Exception as e:
        logger.error(f"خبریں حاصل کرنے میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
