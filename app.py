# filename: app.py

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from config import app_settings
from models import SessionLocal, create_db_and_tables, engine
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
from websocket_manager import manager
from schemas import DailyStatsResponse, SystemStatusResponse, HistoryResponse, NewsResponse, ActiveSignalResponse

# لاگنگ کی ترتیب
logging.basicConfig(
    level=app_settings.LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# FastAPI ایپ
app = FastAPI(
    title=app_settings.PROJECT_NAME,
    version=app_settings.VERSION,
    description="A self-learning AI bot for generating trading signals."
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- انحصار ---
def get_db():
    """ڈیٹا بیس سیشن فراہم کرنے والا انحصار۔"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- پس منظر کے کام ---
async def start_background_tasks():
    """شیڈیولر کو شروع کرتا ہے جو پس منظر کے کاموں کو چلاتا ہے۔"""
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        logger.info("شیڈیولر پہلے سے چل رہا ہے۔")
        return

    logger.info(">>> پس منظر کے کام شروع ہو رہے ہیں...")
    scheduler = AsyncIOScheduler(timezone="UTC")
    app.state.scheduler = scheduler
    # کاموں کو ان کے وقفے کے مطابق شامل کریں
    scheduler.add_job(check_active_signals_job, IntervalTrigger(seconds=70), id="guardian_engine_job")
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(seconds=180), id="hunter_engine_job")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="news_engine_job", next_run_time=datetime.utcnow())
    scheduler.start()
    logger.info("★★★ شیڈیولر کامیابی سے شروع ہو گیا۔ ★★★")

# --- FastAPI ایونٹس ---
@app.on_event("startup")
async def startup_event():
    """ایپلیکیشن کے شروع ہونے پر چلتا ہے۔"""
    logger.info(f"{app_settings.PROJECT_NAME} سرور شروع ہو رہا ہے...")
    create_db_and_tables()
    logger.info("ڈیٹا بیس کی حالت کی تصدیق ہو گئی۔")
    asyncio.create_task(start_background_tasks())

@app.on_event("shutdown")
async def shutdown_event():
    """ایپلیکیشن کے بند ہونے پر چلتا ہے۔"""
    logger.info("FastAPI سرور بند ہو رہا ہے۔")
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        app.state.scheduler.shutdown()
        logger.info("شیڈیولر کامیابی سے بند ہو گیا۔")

# --- API روٹس ---
@app.get("/health", status_code=200, tags=["System"])
async def health_check():
    """سرور کی صحت کی جانچ کے لیے ایک سادہ اینڈ پوائنٹ۔"""
    return {"status": "ok"}

@app.get("/api/active-signals", response_model=List[ActiveSignalResponse], tags=["Signals"])
async def get_active_signals(db: Session = Depends(get_db)):
    """تمام فعال ٹریڈنگ سگنلز کی فہرست واپس کرتا ہے۔"""
    signals = crud.get_all_active_signals_from_db(db)
    return signals

@app.get("/api/daily-stats", response_model=DailyStatsResponse, tags=["Stats"])
async def get_daily_stats_endpoint(db: Session = Depends(get_db)):
    """آج کے اعداد و شمار (TP/SL ہٹس، ون ریٹ) واپس کرتا ہے۔"""
    stats = crud.get_daily_stats(db)
    return stats

@app.get("/api/history", response_model=List[HistoryResponse], tags=["Stats"])
async def get_history(db: Session = Depends(get_db)):
    """مکمل شدہ ٹریڈز کی تاریخ واپس کرتا ہے۔"""
    trades = crud.get_completed_trades(db)
    return trades

@app.get("/api/news", response_model=Optional[NewsResponse], tags=["Market Data"])
async def get_news(db: Session = Depends(get_db)):
    """کیش شدہ مارکیٹ کی خبریں واپس کرتا ہے۔"""
    news_content = crud.get_cached_news(db)
    if news_content and "articles_by_symbol" in news_content:
        return {"articles_by_symbol": news_content["articles_by_symbol"]}
    return None

@app.get("/api/system-status", response_model=SystemStatusResponse, tags=["System"])
async def get_system_status():
    """سسٹم کی مجموعی حالت (سرور، شیڈیولر، ڈیٹا بیس، API کیز) واپس کرتا ہے۔"""
    from key_manager import key_manager
    scheduler_running = hasattr(app.state, "scheduler") and app.state.scheduler.running
    db_status = "Disconnected"
    try:
        with engine.connect():
            db_status = "Connected"
    except Exception:
        db_status = "Connection Error"
    
    # اصلاح: key_manager کی حالت کو بہتر طریقے سے ظاہر کیا گیا ہے
    return {
        "server_status": "Online",
        "timestamp_utc": datetime.utcnow(),
        "scheduler_status": "Running" if scheduler_running else "Stopped",
        "database_status": db_status,
        "key_status": {
            "total_keys": len(key_manager.keys) + len(key_manager.limited_keys),
            "available_keys": len(key_manager.keys),
            "limited_keys_now": len(key_manager.limited_keys)
        }
    }

# --- WebSocket ---
@app.websocket("/ws/live-signals")
async def websocket_endpoint(websocket: WebSocket):
    """لائیو سگنل اپ ڈیٹس کے لیے WebSocket کنکشن کو ہینڈل کرتا ہے۔"""
    await manager.connect(websocket)
    try:
        while True:
            # کلائنٹ سے آنے والے پیغامات کا انتظار کریں (اگر ضرورت ہو)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- اسٹیٹک فائلز ---
# فرنٹ اینڈ فائلوں کو پیش کرنے کے لیے
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
