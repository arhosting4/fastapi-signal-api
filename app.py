import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from config import app_settings, trading_settings # trading_settings کو امپورٹ کیا
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ★★★ درست شدہ کلین اپ فنکشن ★★★
def cleanup_weekend_signals():
    """
    ہفتے کے آخر میں تمام پرانے سگنلز کو بند کرتا ہے تاکہ نیا ہفتہ صاف شروع ہو۔
    """
    logger.info("🧹 ہفتہ وار کلین اپ کا کام شروع کیا جا رہا ہے...")
    db = SessionLocal()
    try:
        # 0 = پیر, 4 = جمعہ, 6 = اتوار
        current_weekday = datetime.utcnow().weekday()
        market_type_to_close = None
        
        # جمعہ کی رات (UTC) فاریکس مارکیٹ بند ہونے کے بعد
        if current_weekday == 4: 
            market_type_to_close = "forex"
            logger.info("🧹 آج جمعہ ہے۔ فاریکس سگنلز کو بند کرنے کے لیے چیک کیا جا رہا ہے۔")
        # اتوار کی رات (UTC) کرپٹو مارکیٹ کے بعد
        elif current_weekday == 6: 
            market_type_to_close = "crypto"
            logger.info("🧹 آج اتوار ہے۔ کرپٹو سگنلز کو بند کرنے کے لیے چیک کیا جا رہا ہے۔")

        if not market_type_to_close:
            logger.info("🧹 آج کلین اپ کا دن نہیں ہے۔ کام ختم۔")
            return

        all_signals = crud.get_all_active_signals_from_db(db)
        signals_to_close = []
        
        if market_type_to_close == "forex":
            forex_pairs = set(trading_settings.WEEKDAY_PRIMARY + trading_settings.WEEKDAY_BACKUP)
            signals_to_close = [s for s in all_signals if s.symbol in forex_pairs]
        elif market_type_to_close == "crypto":
            crypto_pairs = set(trading_settings.WEEKEND_PRIMARY + trading_settings.WEEKEND_BACKUP)
            signals_to_close = [s for s in all_signals if s.symbol in crypto_pairs]
        
        if not signals_to_close:
            logger.info(f"🧹 بند کرنے کے لیے کوئی فعال {market_type_to_close} سگنل نہیں ملا۔")
            return

        for signal in signals_to_close:
            logger.info(f"🧹 ہفتے کے آخر کا کلین اپ: سگنل {signal.symbol} کو بند کیا جا رہا ہے۔")
            # قیمت کے لیے انٹری قیمت استعمال کریں کیونکہ اصل قیمت دستیاب نہیں ہوگی
            crud.close_and_archive_signal(
                db, signal.signal_id, "weekend_close", 
                signal.entry_price, "Automated weekend/market closure"
            )
        logger.info(f"🧹 کل {len(signals_to_close)} سگنلز کامیابی سے بند کر دیے گئے۔")

    except Exception as e:
        logger.error(f"🧹 ہفتہ وار کلین اپ میں خرابی: {e}", exc_info=True)
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def start_background_tasks():
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        return

    logger.info(">>> پس منظر کے کام شروع ہو رہے ہیں...")
    scheduler = AsyncIOScheduler(timezone="UTC")
    app.state.scheduler = scheduler
    
    scheduler.add_job(check_active_signals_job, IntervalTrigger(seconds=120), id="guardian_engine_job")
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(seconds=120), id="hunter_engine_job")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="news_engine_job")
    scheduler.add_job(cleanup_weekend_signals, CronTrigger(hour=22, minute=5, timezone='UTC'), id='cleanup_job')
    
    scheduler.start()
    logger.info("★★★ شیڈیولر کامیابی سے شروع ہو گیا۔ ★★★")

@app.on_event("startup")
async def startup_event():
    logger.info(f"{app_settings.PROJECT_NAME} سرور شروع ہو رہا ہے...")
    create_db_and_tables()
    logger.info("ڈیٹا بیس کی حالت کی تصدیق ہو گئی۔")
    logger.info("ایپلیکیشن کے آغاز پر خبروں کا کیش فوری طور پر اپ ڈیٹ کیا جا رہا ہے...")
    asyncio.create_task(update_economic_calendar_cache())
    asyncio.create_task(start_background_tasks())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FastAPI سرور بند ہو رہا ہے۔")
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        app.state.scheduler.shutdown()
        logger.info("شیڈیولر کامیابی سے بند ہو گیا۔")

@app.get("/health", status_code=200, tags=["System"])
async def health_check():
    return {"status": "ok"}

@app.get("/api/active-signals", response_model=List[ActiveSignalResponse], tags=["Signals"])
async def get_active_signals(db: Session = Depends(get_db)):
    signals = crud.get_all_active_signals_from_db(db)
    return signals

@app.get("/api/daily-stats", response_model=DailyStatsResponse, tags=["Stats"])
async def get_daily_stats_endpoint(db: Session = Depends(get_db)):
    stats = crud.get_daily_stats(db)
    return stats

@app.get("/api/history", response_model=List[HistoryResponse], tags=["Stats"])
async def get_history(db: Session = Depends(get_db)):
    trades = crud.get_completed_trades(db)
    return trades

@app.get("/api/news", response_model=Optional[NewsResponse], tags=["Market Data"])
async def get_news(db: Session = Depends(get_db)):
    news_content = crud.get_cached_news(db)
    if news_content and "articles_by_symbol" in news_content:
        return {"articles_by_symbol": news_content["articles_by_symbol"]}
    return None

@app.get("/api/system-status", response_model=SystemStatusResponse, tags=["System"])
async def get_system_status():
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
        "key_status": {
            "total_keys": len(key_manager.all_keys),
            "assigned_keys": len(key_manager.pair_to_key_map),
            "backup_keys": len(key_manager.key_pool)
        }
    }

@app.websocket("/ws/live-signals")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
