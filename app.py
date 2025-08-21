# filename: app.py

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
from config import app_settings, trading_settings
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

# --- نیا اور بہتر کلین اپ فنکشن ---
def cleanup_weekend_signals():
    """
    ہفتے کے آخر میں تمام پرانے سگنلز کو بند کرتا ہے تاکہ نیا ہفتہ صاف شروع ہو۔
    یہ فنکشن پاکستان کے مقامی وقت کے مطابق چلتا ہے۔
    """
    logger.info("🧹 ہفتہ وار کلین اپ کا کام شروع کیا جا رہا ہے (PKT)...")
    db = SessionLocal()
    try:
        # 0 = پیر, 5 = ہفتہ, 6 = اتوار
        # ہم پاکستان کے ٹائم زون میں ہیں، لیکن weekday() لوکل ٹائم نہیں جانتا، اس لیے UTC استعمال کریں گے
        # اور شیڈیولر میں ٹائم زون سیٹ کریں گے۔
        current_weekday_utc = datetime.utcnow().weekday()
        market_type_to_close = None
        
        # ہفتہ کی صبح (UTC میں جمعہ کی رات کے بعد) - فاریکس بند کریں
        if current_weekday_utc == 5: 
            market_type_to_close = "forex"
            logger.info("🧹 آج ہفتہ ہے۔ فاریکس سگنلز کو بند کرنے کے لیے چیک کیا جا رہا ہے۔")
        # پیر کی صبح (UTC میں اتوار کی رات کے بعد) - کرپٹو بند کریں
        elif current_weekday_utc == 0: 
            market_type_to_close = "crypto"
            logger.info("🧹 آج پیر ہے۔ کرپٹو سگنلز کو بند کرنے کے لیے چیک کیا جا رہا ہے۔")

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
        return

    logger.info(">>> پس منظر کے کام شروع ہو رہے ہیں...")
    # ★★★ نئی تبدیلی: شیڈیولر کو پاکستان کا ٹائم زون دیا گیا ★★★
    scheduler = AsyncIOScheduler(timezone="Asia/Karachi")
    app.state.scheduler = scheduler
    
    scheduler.add_job(check_active_signals_job, IntervalTrigger(seconds=120), id="guardian_engine_job")
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(seconds=180), id="hunter_engine_job")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="news_engine_job")
    
    # --- نیا شیڈول کام (پاکستان ٹائم کے مطابق) ---
    # ہفتہ کی صبح 3:05 پر فاریکس سگنلز بند کرنے کے لیے
    scheduler.add_job(cleanup_weekend_signals, CronTrigger(day_of_week='sat', hour=3, minute=5), id='forex_cleanup_job')
    # پیر کی صبح 3:05 پر کرپٹو سگنلز بند کرنے کے لیے
    scheduler.add_job(cleanup_weekend_signals, CronTrigger(day_of_week='mon', hour=3, minute=5), id='crypto_cleanup_job')
    
    scheduler.start()
    logger.info("★★★ شیڈیولر کامیابی سے شروع ہو گیا۔ ★★★")

# --- FastAPI ایونٹس ---
@app.on_event("startup")
async def startup_event():
    """ایپلیکیشن کے شروع ہونے پر چلتا ہے۔"""
    logger.info(f"{app_settings.PROJECT_NAME} سرور شروع ہو رہا ہے...")
    create_db_and_tables()
    logger.info("ڈیٹا بیس کی حالت کی تصدیق ہو گئی۔")
    
    # ایپلیکیشن شروع ہوتے ہی خبروں کو فوری طور پر ایک بار لوڈ کریں
    logger.info("ایپلیکیشن کے آغاز پر خبروں کا کیش فوری طور پر اپ ڈیٹ کیا جا رہا ہے...")
    asyncio.create_task(update_economic_calendar_cache())
    
    # باقی پس منظر کے کاموں کو معمول کے مطابق شروع کریں
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
        "key_status": {
            "total_keys": len(key_manager.all_keys),
            "assigned_keys": len(key_manager.pair_to_key_map),
            "backup_keys": len(key_manager.key_pool)
        }
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
# اس بات کو یقینی بنائیں کہ 'frontend' نامی فولڈر موجود ہے
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
