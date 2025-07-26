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
from feedback_checker import check_active_signals_job, price_stream_logic
from sentinel import update_economic_calendar_cache
from websocket_manager import manager

# لاگنگ سیٹ اپ
# ہم ماڈیول کا نام شامل کر رہے ہیں تاکہ پتہ چلے کہ لاگ کہاں سے آ رہا ہے
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
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

# ==============================================================================
# پس منظر کے تمام کاموں کو چلانے کے لیے ایک مرکزی فنکشن
# ==============================================================================
async def start_background_tasks():
    """
    یہ فنکشن تمام پس منظر کے کاموں کو شروع کرتا ہے:
    1. شیڈیولر (سگنل ہنٹنگ، فیڈ بیک چیکنگ، نیوز اپ ڈیٹ)
    2. ریئل ٹائم پرائس سٹریم
    """
    # یہ یقینی بناتا ہے کہ یہ کام صرف ایک بار شروع ہوں
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        logger.info("پس منظر کے کام پہلے ہی چل رہے ہیں۔")
        return

    logger.info(">>> پس منظر کے تمام کام شروع ہو رہے ہیں...")
    
    # 1. شیڈیولر شروع کریں
    scheduler = AsyncIOScheduler(timezone="UTC")
    
    def system_heartbeat_job():
        """یہ جاب صرف یہ تصدیق کرنے کے لیے ہے کہ شیڈیولر زندہ ہے۔"""
        logger.info("❤️ سسٹم ہارٹ بیٹ: شیڈیولر زندہ ہے اور پس منظر کے کام فعال ہیں۔")

    # تمام جابز کو شیڈیولر میں شامل کریں
    scheduler.add_job(system_heartbeat_job, IntervalTrigger(minutes=5), id="system_heartbeat")
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=5), id="hunt_for_signals")
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), id="check_active_signals")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="update_news")
    
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("★★★ شیڈیولر کامیابی سے شروع ہو گیا۔ ★★★")

    # 2. ریئل ٹائم پرائس سٹریم کو ایک الگ، نہ رکنے والے ٹاسک میں چلائیں
    logger.info("ریئل ٹائم پرائس سٹریم کو پس منظر میں شروع کیا جا رہا ہے...")
    asyncio.create_task(price_stream_logic())
    logger.info("ریئل ٹائم پرائس سٹریم کامیابی سے شروع ہو گئی۔")


# ==============================================================================
# FastAPI کے ایونٹس اور روٹس
# ==============================================================================

@app.on_event("startup")
async def startup_event():
    """
    FastAPI سرور شروع ہوتے ہی یہ فنکشن چلتا ہے۔
    """
    logger.info("FastAPI سرور شروع ہو رہا ہے...")
    create_db_and_tables()
    logger.info("ڈیٹا بیس کی حالت کی تصدیق ہو گئی۔")
    
    # پس منظر کے کاموں کو یہاں سے شروع کریں
    # asyncio.create_task اس بات کو یقینی بناتا ہے کہ یہ سرور کے آغاز کو بلاک نہ کرے
    asyncio.create_task(start_background_tasks())

@app.on_event("shutdown")
async def shutdown_event():
    """
    FastAPI سرور بند ہوتے ہی یہ فنکشن چلتا ہے۔
    """
    logger.info("FastAPI سرور بند ہو رہا ہے۔")
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        app.state.scheduler.shutdown()
        logger.info("شیڈیولر کامیابی سے بند ہو گیا۔")

# WebSocket اینڈ پوائنٹ
@app.websocket("/ws/live-signals")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # کلائنٹ سے پیغامات کا انتظار کریں (اگر ضرورت ہو)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("کلائنٹ نے WebSocket کنکشن بند کر دیا۔")

# API روٹس
@app.get("/health", status_code=200)
async def health_check():
    """یہ چیک کرنے کے لیے کہ سرور زندہ ہے"""
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

# سٹیٹک فائلز (فرنٹ اینڈ کے لیے)
# یہ آخر میں ہونا چاہیے
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
    
