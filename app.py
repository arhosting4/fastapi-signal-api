# filename: app.py

import os  # ★★★ نیا امپورٹ ★★★
import asyncio
import logging
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException  # ★★★ HTTPException شامل کریں ★★★
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from pydantic import BaseModel  # ★★★ نیا امپورٹ ★★★

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, create_db_and_tables, ActiveSignal
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
from websocket_manager import manager

# لاگنگ کی ترتیب
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ★★★ سیکیورٹی: ماحول سے پاس ورڈ حاصل کریں ★★★
MANUAL_DELETE_PASSWORD = os.getenv("MANUAL_DELETE_PASSWORD")

# FastAPI ایپ کی تعریف
app = FastAPI(title="ScalpMaster AI API")

# CORS مڈل ویئر
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ہیلپر فنکشنز اور ایونٹس
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def start_background_tasks():
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        return
    logger.info(">>> پس منظر کے تمام کام شروع ہو رہے ہیں...")
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(lambda: logger.info("❤️ سسٹم ہارٹ بیٹ: شیڈیولر زندہ ہے۔"), IntervalTrigger(minutes=5), id="system_heartbeat")
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=5), id="hunt_for_signals")
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), id="check_active_signals")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="update_news")
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("★★★ شیڈیولر کامیابی سے شروع ہو گیا۔ ★★★")
    logger.info("پرائس سٹریم غیر فعال ہے۔ قیمتیں ہر منٹ REST API کے ذریعے حاصل کی جائیں گی۔")

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI سرور شروع ہو رہا ہے...")
    create_db_and_tables()
    logger.info("ڈیٹا بیس کی حالت کی تصدیق ہو گئی۔")
    logger.info("پہلی بار خبروں کا کیش اپ ڈیٹ کیا جا رہا ہے...")
    try:
        await update_economic_calendar_cache()
        logger.info("خبروں کا کیش کامیابی سے اپ ڈیٹ ہو گیا۔")
    except Exception as e:
        logger.error(f"شروع میں خبروں کا کیش اپ ڈیٹ کرنے میں ناکامی: {e}", exc_info=True)
    asyncio.create_task(start_background_tasks())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FastAPI سرور بند ہو رہا ہے۔")
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        app.state.scheduler.shutdown()
        logger.info("شیڈیولر کامیابی سے بند ہو گیا۔")

# ★★★ ڈیلیٹ کی درخواست کے لیے ڈیٹا ماڈل ★★★
class DeleteSignalRequest(BaseModel):
    signal_id: str
    password: str

# API روٹس
@app.websocket("/ws/live-signals")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("کلائنٹ نے WebSocket کنکشن بند کر دیا۔")

@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

@app.get("/api/active-signals", response_class=JSONResponse)
async def get_active_signals(db: Session = Depends(get_db)):
    try:
        signals = crud.get_all_active_signals_from_db(db)
        return [signal.as_dict() for signal in signals]
    except Exception as e:
        logger.error(f"فعال سگنلز حاصل کرنے میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

# ★★★ نیا، محفوظ ڈیلیٹ اینڈ پوائنٹ ★★★
@app.post("/api/delete-signal", response_class=JSONResponse)
async def delete_signal_manually(request: DeleteSignalRequest, db: Session = Depends(get_db)):
    """ایک فعال سگنل کو دستی طور پر حذف کرتا ہے۔"""
    
    if not MANUAL_DELETE_PASSWORD:
        logger.error("منتظم کا پاس ورڈ ماحول کے متغیرات میں سیٹ نہیں ہے۔")
        raise HTTPException(status_code=500, detail="Server configuration error: Admin password not set.")

    if request.password != MANUAL_DELETE_PASSWORD:
        logger.warning(f"سگنل {request.signal_id} کو حذف کرنے کی ناکام کوشش: غلط پاس ورڈ۔")
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid password.")

    try:
        signal_to_delete = db.query(ActiveSignal).filter(ActiveSignal.signal_id == request.signal_id).first()
        if not signal_to_delete:
            raise HTTPException(status_code=404, detail="Signal not found in active signals.")

        crud.add_completed_trade_from_active(db, signal_to_delete, "Manually Closed")
        db.delete(signal_to_delete)
        db.commit()

        logger.info(f"سگنل {request.signal_id} کو منتظم نے کامیابی سے حذف کر دیا۔")

        await manager.broadcast({
            "type": "signal_closed",
            "data": {"signal_id": request.signal_id}
        })

        return {"status": "ok", "message": f"Signal {request.signal_id} has been manually closed and moved to history."}

    except Exception as e:
        db.rollback()
        logger.error(f"سگنل {request.signal_id} کو حذف کرنے میں خرابی: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during signal deletion.")

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

# اسٹیٹک فائلیں
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
