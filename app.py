# filename: app.py

import asyncio
import logging
import os
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta

# مقامی امپورٹس
import database_crud as crud
# ★★★ JobLock امپورٹ کو یہاں سے ہٹا دیا گیا ہے ★★★
from models import SessionLocal, create_db_and_tables, engine
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
from websocket_manager import manager
from key_manager import key_manager

# لاگنگ کی ترتیب
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

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

# --- API روٹس ---

@app.get("/api/active-signals", response_class=JSONResponse)
async def get_active_signals(db: Session = Depends(get_db)):
    try:
        signals = crud.get_all_active_signals_from_db(db)
        return [s.as_dict() for s in signals]
    except Exception as e:
        logger.error(f"فعال سگنلز حاصل کرنے میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

@app.get("/api/daily-stats", response_class=JSONResponse)
async def get_daily_stats_endpoint(db: Session = Depends(get_db)):
    try:
        stats = crud.get_daily_stats(db)
        return stats
    except Exception as e:
        logger.error(f"روزانہ کے اعداد و شمار حاصل کرنے میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

# ★★★ مکمل طور پر سادہ کیا گیا فنکشن (بغیر لاک کے) ★★★
async def start_background_tasks():
    """
    پس منظر کے کاموں کو شروع کرتا ہے۔ یہ فرض کرتا ہے کہ صرف ایک ورکر چل رہا ہے۔
    """
    # اگر شیڈیولر پہلے سے چل رہا ہے تو کچھ نہ کریں
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        logger.info("شیڈیولر پہلے سے چل رہا ہے۔")
        return

    logger.info(">>> پس منظر کے کام شروع ہو رہے ہیں (سنگل ورکر موڈ)...")
    
    scheduler = AsyncIOScheduler(timezone="UTC")
    app.state.scheduler = scheduler
    
    def heartbeat_job():
        app.state.last_heartbeat = datetime.utcnow()
        logger.info(f"❤️ سسٹم ہارٹ بیٹ: {app.state.last_heartbeat.isoformat()}")
    
    now = datetime.utcnow()
    
    # ذہین شیڈول (Staggered Jobs)
    scheduler.add_job(heartbeat_job, IntervalTrigger(minutes=15), id="system_heartbeat")
    scheduler.add_job(check_active_signals_job, IntervalTrigger(seconds=70), id="guardian_engine_job", next_run_time=now + timedelta(seconds=5))
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(seconds=180), id="hunter_engine_job", next_run_time=now + timedelta(seconds=40))
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="news_engine_job")
    
    scheduler.start()
    heartbeat_job()
    logger.info("★★★ شیڈیولر کامیابی سے شروع ہو گیا۔ ★★★")
    logger.info(f"نگران انجن ہر 70 سیکنڈ بعد چلے گا۔ اگلی دوڑ: {scheduler.get_job('guardian_engine_job').next_run_time}")
    logger.info(f"شکاری انجن ہر 180 سیکنڈ بعد چلے گا۔ اگلی دوڑ: {scheduler.get_job('hunter_engine_job').next_run_time}")

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI سرور شروع ہو رہا ہے...")
    create_db_and_tables()
    logger.info("ڈیٹا بیس کی حالت کی تصدیق ہو گئی۔")
    
    # خبروں کا کیش اپ ڈیٹ کرنے کا کام اب پس منظر میں ہوگا
    # await update_economic_calendar_cache() 
    
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

@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

@app.get("/api/system-status", response_class=JSONResponse)
async def get_system_status():
    scheduler_running = hasattr(app.state, "scheduler") and app.state.scheduler.running
    last_heartbeat = getattr(app.state, "last_heartbeat", None)
    
    db_status = "Disconnected"
    try:
        with engine.connect() as connection:
            db_status = "Connected"
    except Exception:
        db_status = "Connection Error"

    return {
        "server_status": "Online",
        "timestamp_utc": datetime.utcnow().isoformat(),
        "scheduler_status": "Running" if scheduler_running else "Stopped",
        "last_heartbeat": last_heartbeat.isoformat() if last_heartbeat else "N/A",
        "database_status": db_status,
        "key_status": {
            "guardian_keys_total": len(key_manager.guardian_keys),
            "hunter_keys_total": len(key_manager.hunter_keys),
            "limited_keys_now": len(key_manager.limited_keys)
        }
    }

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
    
