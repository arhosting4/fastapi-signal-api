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
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
from websocket_manager import manager

# لاگنگ سیٹ اپ
# صرف ضروری اور معلوماتی لاگز دکھانے کے لیے فارمیٹ کو صاف کیا گیا
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI ایپ
app = FastAPI(title="ScalpMaster AI API")

# CORS (Cross-Origin Resource Sharing) مڈل ویئر
# یہ فرنٹ اینڈ کو بیک اینڈ سے بات کرنے کی اجازت دیتا ہے
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # تمام اوریجنز کو اجازت دیں
    allow_credentials=True,
    allow_methods=["*"],  # تمام طریقوں (GET, POST, etc.) کو اجازت دیں
    allow_headers=["*"],  # تمام ہیڈرز کو اجازت دیں
)

# ڈیٹا بیس سیشن حاصل کرنے کے لیے انحصار (Dependency)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# WebSocket اینڈ پوائنٹ برائے لائیو سگنلز
@app.websocket("/ws/live-signals")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # کلائنٹ سے آنے والے پیغامات کا انتظار کریں (اگر مستقبل میں ضرورت ہو)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("ایک کلائنٹ نے WebSocket کنکشن بند کر دیا۔")

# API روٹس

# ہیلتھ چیک روٹ: یہ چیک کرنے کے لیے کہ سرور چل رہا ہے
@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

# ہسٹری روٹ: مکمل شدہ ٹریڈز کی تاریخ حاصل کرنے کے لیے
@app.get("/api/history", response_class=JSONResponse)
async def get_history(db: Session = Depends(get_db)):
    try:
        trades = crud.get_completed_trades(db)
        return trades
    except Exception as e:
        logger.error(f"ہسٹری حاصل کرنے میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

# نیوز روٹ: کیش شدہ خبریں حاصل کرنے کے لیے
@app.get("/api/news", response_class=JSONResponse)
async def get_news(db: Session = Depends(get_db)):
    try:
        news = crud.get_cached_news(db)
        if not news or not news.get("articles"):
            return JSONResponse(status_code=404, content={"message": "کوئی خبر نہیں ملی۔"})
        return news
    except Exception as e:
        logger.error(f"خبریں حاصل کرنے میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

# پس منظر کے کام (Background Jobs)

# سرور شروع ہونے پر چلنے والا ایونٹ
@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI ورکر شروع ہو رہا ہے...")
    create_db_and_tables()
    logger.info("ڈیٹا بیس کی حالت کی تصدیق ہو گئی۔")
    
    # سرور شروع ہوتے ہی خبروں کو فوری اپ ڈیٹ کریں
    logger.info("پہلی بار خبروں کا کیش اپ ڈیٹ کیا جا رہا ہے...")
    await update_economic_calendar_cache()
    
    # شیڈیولر کو صرف ایک بار شروع کرنے کی منطق
    if not hasattr(app.state, "scheduler") or not app.state.scheduler.running:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        
        scheduler = AsyncIOScheduler(timezone="UTC")
        
        # ★★★ اصل اور مستحکم فریکوئنسی ★★★
        # ہنٹر کو ہر 5 منٹ بعد چلائیں
        scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=5), id="hunt_for_signals")
        # فیڈ بیک چیکر کو ہر 1 منٹ بعد چلائیں
        scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), id="check_active_signals")
        # نیوز کیش کو ہر 4 گھنٹے بعد اپ ڈیٹ کریں
        scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="update_news")
        
        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("★★★ شیڈیولر کامیابی سے شروع ہو گیا۔ (اصل فریکوئنسی کے ساتھ) ★★★")
    else:
        logger.info("شیڈیولر پہلے ہی کسی دوسرے ورکر کے ذریعے شروع کیا جا چکا ہے۔")

# سرور بند ہونے پر چلنے والا ایونٹ
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FastAPI ورکر بند ہو رہا ہے۔")
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        app.state.scheduler.shutdown()
        logger.info("شیڈیولر بند ہو گیا۔")

# سٹیٹک فائلز (فرنٹ اینڈ کے لیے)
# یہ `frontend` ڈائرکٹری میں موجود HTML, CSS, JS فائلوں کو پیش کرتا ہے
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
