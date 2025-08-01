# filename: app.py

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from config import app_settings, api_settings, trading_settings, strategy_settings # مرکزی کنفیگریشن
# ★★★ غلطی کی درستگی: 'database' کی جگہ 'models' سے امپورٹ کریں ★★★
from models import SessionLocal, create_db_and_tables, engine
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
from websocket_manager import manager
from schemas import DailyStatsResponse, SystemStatusResponse, KeyStatusResponse, HistoryResponse, NewsResponse, ActiveSignalResponse

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

# CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # پروڈکشن میں اسے مخصوص ڈومینز تک محدود کریں
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- انحصار (Dependencies) ---

def get_db():
    """ڈیٹا بیس سیشن فراہم کرنے والا انحصار۔"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- پس منظر کے کام (Background Tasks) ---

async def start_background_tasks():
    """
    پس منظر کے کاموں (سگنل کی تلاش، نگرانی) کو شروع کرتا ہے۔
    یہ فرض کرتا ہے کہ صرف ایک ورکر چل رہا ہے (Gunicorn میں -w 1)۔
    """
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        logger.info("شیڈیولر پہلے سے چل رہا ہے۔ دوبارہ شروع نہیں کیا جا رہا۔")
        return

    logger.info(">>> پس منظر کے کام شروع ہو رہے ہیں...")
    
    scheduler = AsyncIOScheduler(timezone="UTC")
    app.state.scheduler = scheduler
    
    # کاموں کو مختلف اوقات میں شروع کریں تاکہ API کی شرح کی حدود سے بچا جا سکے
    scheduler.add_job(check_active_signals_job, IntervalTrigger(seconds=70), id="guardian_engine_job")
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(seconds=180), id="hunter_engine_job")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="news_engine_job", next_run_time=datetime.utcnow())
    
    scheduler.start()
    logger.info("★★★ شیڈیولر کامیابی سے شروع ہو گیا۔ ★★★")

# --- FastAPI ایونٹس ---

@app.on_event("startup")
async def startup_event():
    """ایپلیکیشن شروع ہونے پر چلنے والا ایونٹ۔"""
    logger.info(f"{app_settings.PROJECT_NAME} سرور شروع ہو رہا ہے...")
    create_db_and_tables()
    logger.info("ڈیٹا بیس کی حالت کی تصدیق ہو گئی۔")
    asyncio.create_task(start_background_tasks())

@app.on_event("shutdown")
async def shutdown_event():
    """ایپلیکیشن بند ہونے پر چلنے والا ایونٹ۔"""
    logger.info("FastAPI سرور بند ہو رہا ہے۔")
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        app.state.scheduler.shutdown()
        logger.info("شیڈیولر کامیابی سے بند ہو گیا۔")

# --- API روٹس ---

@app.get("/health", status_code=200, tags=["System"])
async def health_check():
    """سسٹم کی صحت کی جانچ کے لیے سادہ اینڈ پوائنٹ۔"""
    return {"status": "ok"}

@app.get("/api/active-signals", response_model=List[ActiveSignalResponse], tags=["Signals"])
async def get_active_signals(db: Session = Depends(get_db)):
    """تمام فعال ٹریڈنگ سگنلز واپس کرتا ہے۔"""
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
    return {"articles_by_symbol": news_content.get("articles_by_symbol", {})} if news_content else None

@app.get("/api/system-status", response_model=SystemStatusResponse, tags=["System"])
async def get_system_status():
    """سسٹم کی موجودہ حالت (شیڈیولر، ڈیٹا بیس، API کیز) واپس کرتا ہے۔"""
    from key_manager import key_manager # صرف یہاں امپورٹ کریں تاکہ سرکلر انحصار سے بچا جا سکے
    
    scheduler_running = hasattr(app.state, "scheduler") and app.state.scheduler.running
    db_status = "Disconnected"
    try:
        with engine.connect():
            db_status = "Connected"
    except Exception:
        db_status = "Connection Error"

    return {
        "server_status": "Online",
        "timestamp_utc": datetime.utcnow(),
        "scheduler_status": "Running" if scheduler_running else "Stopped",
        "database_status": db_status,
        "key_status": {
            "guardian_keys_total": len(key_manager.guardian_keys),
            "hunter_keys_total": len(key_manager.hunter_keys),
            "limited_keys_now": len(key_manager.limited_keys)
        }
    }

# --- WebSocket ---

@app.websocket("/ws/live-signals")
async def websocket_endpoint(websocket: WebSocket):
    """لائیو سگنل اپ ڈیٹس کے لیے WebSocket کنکشن۔"""
    await manager.connect(websocket)
    try:
        while True:
            # کلائنٹ سے آنے والے پیغامات کو سنیں (اگر ضرورت ہو)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- اسٹیٹک فائلز ---

# فرنٹ اینڈ فائلوں کو پیش کرنے کے لیے اسٹیٹک ڈائرکٹری کو ماؤنٹ کریں
# یہ یقینی بنائیں کہ 'frontend' نامی فولڈر موجود ہے
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
    
