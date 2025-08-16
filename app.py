import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
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
from roster_manager import get_forex_pairs

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

async def cleanup_weekend_signals():
    """
    صرف فاریکس سگنلز کو ہفتے کے آخر میں بند کرتا ہے اور فرنٹ اینڈ کو مطلع کرتا ہے۔
    """
    logger.info("🧹 ہفتے کے آخر کی صفائی کا کام شروع ہو رہا ہے...")
    db = SessionLocal()
    try:
        forex_pairs = get_forex_pairs()
        if not forex_pairs:
            logger.warning("🧹 صفائی کا کام روکا گیا: فاریکس جوڑوں کی فہرست نہیں ملی۔")
            return

        # ڈیٹا بیس سے صرف فاریکس کے فعال سگنلز حاصل کریں
        signals_to_close = db.query(crud.ActiveSignal).filter(
            crud.ActiveSignal.symbol.in_(forex_pairs)
        ).all()

        if not signals_to_close:
            logger.info("🧹 کوئی فعال فاریکس سگنل بند کرنے کے لیے نہیں ملا۔")
            return

        logger.info(f"🧹 {len(signals_to_close)} فعال فاریکس سگنلز کو بند کیا جا رہا ہے...")
        closed_count = 0
        for signal in signals_to_close:
            signal_id_to_broadcast = signal.signal_id # ID کو پہلے محفوظ کریں
            
            success = crud.close_and_archive_signal(
                db=db,
                signal_id=signal.signal_id,
                outcome="weekend_close",
                close_price=signal.entry_price,
                reason_for_closure="Market closed for the weekend"
            )
            if success:
                closed_count += 1
                # فرنٹ اینڈ کو اطلاع دیں
                logger.info(f"📡 کلائنٹس کو سگنل {signal_id_to_broadcast} کے بند ہونے کی اطلاع دی جا رہی ہے...")
                await manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal_id_to_broadcast}})
        
        logger.info(f"🧹 {closed_count} فاریکس سگنلز کامیابی سے بند ہو گئے۔")

    except Exception as e:
        logger.error(f"🧹 ہفتے کے آخر کی صفائی میں خرابی: {e}", exc_info=True)
    finally:
        db.close()

async def start_background_tasks():
    """شیڈیولر کو شروع کرتا ہے جو پس منظر کے کاموں کو چلاتا ہے۔"""
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        logger.info("شیڈیولر پہلے سے چل رہا ہے۔")
        return

    logger.info(">>> پس منظر کے کام شروع ہو رہے ہیں...")
    scheduler = AsyncIOScheduler(timezone="UTC")
    app.state.scheduler = scheduler
    
    scheduler.add_job(check_active_signals_job, IntervalTrigger(seconds=120), id="guardian_engine_job")
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(seconds=180), id="hunter_engine_job")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="news_engine_job", next_run_time=datetime.utcnow())
    
    # ہر جمعہ کو 21:05 UTC پر چلے گا
    scheduler.add_job(cleanup_weekend_signals, CronTrigger(day_of_week='fri', hour=21, minute=5, timezone='UTC'), id="cleanup_weekend_signals")
    
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
    
    return {
        "server_status": "Online",
        "timestamp_utc": datetime.utcnow(),
        "scheduler_status": "Running" if scheduler_running else "Stopped",
        "database_status": db_status,
        "key_status": key_manager.get_key_status() # key_manager سے اسٹیٹس حاصل کریں
    }

# --- WebSocket ---
@app.websocket("/ws/live-signals")
async def websocket_endpoint(websocket: WebSocket):
    """لائیو سگنل اپ ڈیٹس کے لیے WebSocket کنکشن کو ہینڈل کرتا ہے۔"""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- اسٹیٹک فائلز ---
# فرنٹ اینڈ فائلوں کو پیش کرنے کے لیے
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
