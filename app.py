# filename: app.py

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import AsyncGenerator

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# مقامی امپورٹس
# بہتر ساخت کے لیے، ڈیٹا بیس سے متعلق تمام چیزیں ایک ہی جگہ پر
from database import SessionLocal, create_db_and_tables, engine
import database_crud as crud
from schemas import ActiveSignalResponse, DailyStatsResponse, SystemStatusResponse, HistoryResponse, NewsResponse
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
from websocket_manager import manager
from key_manager import key_manager
from config import api_settings # مرکزی کنفیگریشن

# --- لاگنگ کی ترتیب ---
logging.basicConfig(
    level=api_settings.LOG_LEVEL.upper(),
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
)
logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# --- پس منظر کے کام اور لائف سائیکل مینیجر ---
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    ایپلیکیشن کے آغاز اور اختتام پر چلنے والے ایونٹس کو منظم کرتا ہے۔
    """
    logger.info("🚀 FastAPI سرور شروع ہو رہا ہے...")
    
    # ڈیٹا بیس کی تصدیق
    create_db_and_tables()
    logger.info("✅ ڈیٹا بیس کی حالت کی تصدیق ہو گئی۔")

    # شیڈیولر کی ترتیب
    # یہ فرض کیا جاتا ہے کہ یہ صرف ایک ورکر کے ماحول میں چل رہا ہے۔
    # متعدد ورکرز کے لیے، Redis یا DB پر مبنی لاک کی ضرورت ہوگی۔
    scheduler = AsyncIOScheduler(timezone="UTC")
    
    # کاموں کو ذہانت سے ترتیب دیں تاکہ API کی شرح کی حد سے بچا جا سکے
    now = datetime.utcnow()
    scheduler.add_job(check_active_signals_job, IntervalTrigger(seconds=70), id="guardian_engine_job", next_run_time=now + timedelta(seconds=5))
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(seconds=180), id="hunter_engine_job", next_run_time=now + timedelta(seconds=40))
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="news_engine_job", next_run_time=now + timedelta(seconds=10))
    
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("★★★ پس منظر کے کاموں کا شیڈیولر کامیابی سے شروع ہو گیا۔ ★★★")
    
    yield
    
    # ایپلیکیشن بند ہونے پر صفائی
    logger.info("🛑 FastAPI سرور بند ہو رہا ہے۔")
    if app.state.scheduler.running:
        app.state.scheduler.shutdown()
        logger.info("✅ شیڈیولر کامیابی سے بند ہو گیا۔")


# --- FastAPI ایپ کی مثال ---
app = FastAPI(
    title="ScalpMaster AI API",
    description="ایک ذہین ٹریڈنگ سگنل بوٹ جو مارکیٹ کا تجزیہ کرتا ہے اور ریئل ٹائم الرٹس فراہم کرتا ہے۔",
    version="1.0.0",
    lifespan=lifespan
)

# CORS مڈل ویئر
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # پروڈکشن میں اسے مخصوص ڈومینز تک محدود کریں
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- انحصار (Dependency) ---
def get_db() -> Session:
    """
    ہر درخواست کے لیے ایک نیا ڈیٹا بیس سیشن بناتا اور فراہم کرتا ہے۔
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API روٹس ---

@app.get("/api/active-signals", response_model=List[ActiveSignalResponse])
async def get_active_signals(db: Session = Depends(get_db)):
    """تمام فعال ٹریڈنگ سگنلز کی فہرست واپس کرتا ہے۔"""
    try:
        signals = crud.get_all_active_signals_from_db(db)
        return [s.as_dict() for s in signals]
    except Exception as e:
        logger.error(f"فعال سگنلز حاصل کرنے میں خرابی: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while fetching signals.")

@app.get("/api/daily-stats", response_model=DailyStatsResponse)
async def get_daily_stats_endpoint(db: Session = Depends(get_db)):
    """آج کے اعداد و شمار (TP/SL ہٹس وغیرہ) واپس کرتا ہے۔"""
    try:
        return crud.get_daily_stats(db)
    except Exception as e:
        logger.error(f"روزانہ کے اعداد و شمار حاصل کرنے میں خرابی: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while fetching stats.")

@app.get("/api/history", response_model=List[HistoryResponse])
async def get_history(db: Session = Depends(get_db)):
    """مکمل شدہ ٹریڈز کی تاریخ واپس کرتا ہے۔"""
    try:
        return crud.get_completed_trades(db)
    except Exception as e:
        logger.error(f"ہسٹری حاصل کرنے میں خرابی: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while fetching history.")

@app.get("/api/news", response_model=Optional[NewsResponse])
async def get_news(db: Session = Depends(get_db)):
    """کیش شدہ مارکیٹ کی خبریں واپس کرتا ہے۔"""
    try:
        news = crud.get_cached_news(db)
        if not news:
            return None
        return news
    except Exception as e:
        logger.error(f"خبریں حاصل کرنے میں خرابی: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while fetching news.")

@app.get("/api/system-status", response_model=SystemStatusResponse)
async def get_system_status():
    """سسٹم کی موجودہ حالت کی تفصیلات فراہم کرتا ہے۔"""
    scheduler = app.state.scheduler
    scheduler_running = scheduler and scheduler.running
    
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

@app.get("/health", status_code=200, include_in_schema=False)
async def health_check():
    """صحت کی جانچ کا اینڈ پوائنٹ جو Render جیسے ہوسٹنگ پلیٹ فارمز کے لیے ہے۔"""
    return {"status": "ok"}

@app.websocket("/ws/live-signals")
async def websocket_endpoint(websocket: WebSocket):
    """ریئل ٹائم سگنل اپ ڈیٹس کے لیے WebSocket کنکشن۔"""
    await manager.connect(websocket)
    try:
        while True:
            # کلائنٹ سے آنے والے پیغامات کو سنتے رہیں
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket میں ایک خرابی پیش آئی: {e}")
        manager.disconnect(websocket)

# فرنٹ اینڈ فائلوں کو پیش کرنے کے لیے اسٹیٹک ڈائرکٹری کو ماؤنٹ کریں
# یہ یقینی بنائیں کہ 'frontend' نامی فولڈر موجود ہے
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
        
