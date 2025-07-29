# filename: app.py

import asyncio
import logging
import os
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from typing import Dict
from pydantic import BaseModel

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, create_db_and_tables, engine
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
from websocket_manager import manager
from key_manager import key_manager # ★★★ ہمارا نیا ملٹی پول مینیجر ★★★

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

# API روٹس
@app.get("/api/active-signals", response_class=JSONResponse)
async def get_active_signals(db: Session = Depends(get_db)):
    """تمام فعال سگنلز کو ڈیٹا بیس سے حاصل کرتا ہے۔"""
    try:
        signals = crud.get_all_active_signals_from_db(db)
        return [s.as_dict() for s in signals]
    except Exception as e:
        logger.error(f"فعال سگنلز حاصل کرنے میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

class PasswordData(BaseModel):
    password: str

@app.post("/api/delete-signal/{signal_id}", response_class=JSONResponse)
async def delete_signal_endpoint(signal_id: str, password_data: PasswordData, db: Session = Depends(get_db)):
    """
    ایک فعال سگنل کو دستی طور پر بند کرتا ہے۔
    نوٹ: اس کو بہتر بنانے کی ضرورت ہے تاکہ بند ہونے کی وجہ اور قیمت بھی شامل کی جا سکے۔
    """
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
    
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ایڈمن پاس ورڈ سرور پر کنفیگر نہیں ہے۔")
    if not password_data.password or password_data.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="غلط پاس ورڈ")
    
    # ★★★ یہاں بہتری کی گنجائش ہے ★★★
    # فی الحال، ہم ایک ڈیفالٹ وجہ اور قیمت کے ساتھ بند کر رہے ہیں۔
    # اسے فرنٹ اینڈ سے بھیجا جا سکتا ہے۔
    success = crud.close_and_archive_signal(
        db=db, 
        signal_id=signal_id,
        outcome="manual_close",
        close_price=0, # یہاں لائیو قیمت ہونی چاہیے
        reason_for_closure="Manually closed by admin"
    )
    
    if success:
        await manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal_id}})
        return {"detail": f"سگنل {signal_id} کامیابی سے بند کر دیا گیا۔"}
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"فعال سگنل {signal_id} نہیں ملا۔")

async def start_background_tasks():
    """پس منظر کے تمام کاموں کو شروع کرتا ہے۔"""
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        logger.info("پس منظر کے کام پہلے ہی چل رہے ہیں۔")
        return

    logger.info(">>> پس منظر کے تمام کام شروع ہو رہے ہیں...")
    
    scheduler = AsyncIOScheduler(timezone="UTC")
    app.state.scheduler = scheduler
    
    def heartbeat_job():
        app.state.last_heartbeat = datetime.utcnow()
        logger.info(f"❤️ سسٹم ہارٹ بیٹ: شیڈیولر زندہ ہے۔ آخری دھڑکن: {app.state.last_heartbeat.isoformat()}")
    
    # ★★★ نیا، تیز رفتار اور ذہین شیڈول ★★★
    scheduler.add_job(heartbeat_job, IntervalTrigger(minutes=5), id="system_heartbeat")
    # ہنٹر اب ہر 60 سیکنڈ بعد چلے گا تاکہ کسی موقع کو ضائع نہ کرے
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(seconds=60), id="hunt_for_signals")
    # فیڈ بیک چیکر بھی زیادہ تیزی سے چلے گا
    scheduler.add_job(check_active_signals_job, IntervalTrigger(seconds=45), id="check_active_signals")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="update_news")
    
    scheduler.start()
    heartbeat_job() # پہلی بار فوراً چلائیں
    logger.info("★★★ شیڈیولر کامیابی سے شروع ہو گیا۔ ★★★")

@app.on_event("startup")
async def startup_event():
    """سرور شروع ہونے پر چلنے والے ایونٹس۔"""
    logger.info("FastAPI سرور شروع ہو رہا ہے...")
    create_db_and_tables()
    logger.info("ڈیٹا بیس کی حالت کی تصدیق ہو گئی۔")
    
    logger.info("پہلی بار خبروں کا کیش اپ ڈیٹ کیا جا رہا ہے...")
    await update_economic_calendar_cache()
    logger.info("خبروں کا کیش کامیابی سے اپ ڈیٹ ہو گیا۔")
    
    asyncio.create_task(start_background_tasks())

@app.on_event("shutdown")
async def shutdown_event():
    """سرور بند ہونے پر چلنے والے ایونٹس۔"""
    logger.info("FastAPI سرور بند ہو رہا ہے۔")
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        app.state.scheduler.shutdown()
        logger.info("شیڈیولر کامیابی سے بند ہو گیا۔")

@app.websocket("/ws/live-signals")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket کنکشن کو سنبھالتا ہے۔"""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("کلائنٹ نے WebSocket کنکشن بند کر دیا۔")

@app.get("/health", status_code=200)
async def health_check():
    """ایک سادہ ہیلتھ چیک جو صرف سروس کے چلنے کی تصدیق کرتا ہے۔"""
    return {"status": "ok"}

# ... (باقی کے API روٹس جیسے /api/system-status, /api/history, /api/news میں کوئی تبدیلی نہیں)
# وہ ویسے ہی کام کرتے رہیں گے۔

@app.get("/api/system-status", response_class=JSONResponse)
async def get_system_status():
    """سسٹم کی صحت اور کارکردگی کے بارے میں تفصیلی معلومات فراہم کرتا ہے۔"""
    scheduler_running = hasattr(app.state, "scheduler") and app.state.scheduler.running
    last_heartbeat = getattr(app.state, "last_heartbeat", None)
    
    db_status = "Disconnected"
    try:
        connection = engine.connect()
        connection.close()
        db_status = "Connected"
    except Exception as e:
        logger.error(f"ڈیٹا بیس کنکشن چیک کرنے میں خرابی: {e}")
        db_status = "Connection Error"

    # ★★★ کی مینیجر کی حیثیت کو مزید تفصیلی بنایا جا سکتا ہے ★★★
    # لیکن فی الحال اسے سادہ رکھتے ہیں
    
    return {
        "server_status": "Online",
        "timestamp_utc": datetime.utcnow().isoformat(),
        "scheduler_status": "Running" if scheduler_running else "Stopped",
        "last_heartbeat": last_heartbeat.isoformat() if last_heartbeat else "N/A",
        "database_status": db_status,
    }

@app.get("/api/history", response_class=JSONResponse)
async def get_history(db: Session = Depends(get_db)):
    """مکمل شدہ ٹریڈز کی تاریخ حاصل کرتا ہے۔"""
    try:
        trades = crud.get_completed_trades(db)
        return trades
    except Exception as e:
        logger.error(f"ہسٹری حاصل کرنے میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

@app.get("/api/news", response_class=JSONResponse)
async def get_news(db: Session = Depends(get_db)):
    """کیش شدہ خبریں حاصل کرتا ہے۔"""
    try:
        news = crud.get_cached_news(db)
        return news
    except Exception as e:
        logger.error(f"خبریں حاصل کرنے میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
