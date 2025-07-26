# filename: app.py

import asyncio
import logging
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, create_db_and_tables
from websocket_manager import manager

# --- ہائبرڈ سسٹم کے لیے نئے امپورٹس ---
from crypto_listener import binance_websocket_listener
from gold_hunter import hunt_for_gold_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache

# لاگنگ سیٹ اپ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI ایپ
app = FastAPI(title="ScalpMaster AI v3.0 - Hybrid Engine")

# CORS
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# DB انحصار
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# WebSocket اینڈ پوائنٹ (کوئی تبدیلی نہیں)
@app.websocket("/ws/live-signals")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("کلائنٹ نے WebSocket کنکشن بند کر دیا۔")

# API روٹس (کوئی تبدیلی نہیں)
@app.get("/health", status_code=200)
async def health_check(): return {"status": "ok"}

@app.get("/api/history", response_class=JSONResponse)
async def get_history(db: Session = Depends(get_db)):
    return crud.get_completed_trades(db)

@app.get("/api/news", response_class=JSONResponse)
async def get_news(db: Session = Depends(get_db)):
    return crud.get_cached_news(db)

# --- پس منظر کے کام (اپ گریڈ شدہ) ---
@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI ورکر شروع ہو رہا ہے (v3.0 ہائبرڈ انجن)...")
    create_db_and_tables()
    logger.info("ڈیٹا بیس کی حالت کی تصدیق ہو گئی۔")
    
    # کرپٹو لسنر کو ایک مستقل پس منظر کے ٹاسک کے طور پر چلائیں
    asyncio.create_task(binance_websocket_listener())
    logger.info("Binance WebSocket لسنر پس منظر میں شروع ہو گیا۔")
    
    # شیڈیولر کو صرف ایک بار شروع کریں
    if not hasattr(app.state, "scheduler") or not app.state.scheduler.running:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        
        scheduler = AsyncIOScheduler(timezone="UTC")
        # شیڈیولر اب صرف وقفے والے کاموں کو سنبھالے گا
        scheduler.add_job(hunt_for_gold_signals_job, IntervalTrigger(minutes=5), id="hunt_for_gold")
        scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), id="check_active_signals")
        scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="update_news")
        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("★★★ APScheduler کامیابی سے شروع ہو گیا۔ ★★★")
    else:
        logger.info("شیڈیولر پہلے ہی شروع کیا جا چکا ہے۔")

# سٹیٹک فائلز
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
