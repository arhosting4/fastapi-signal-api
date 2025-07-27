# filename: app.py

import asyncio
import logging
import os
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException, status, Header
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from typing import Optional

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, create_db_and_tables
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
from websocket_manager import manager

# ==============================================================================
# ★★★ بنیادی سیکیورٹی اپ گریڈ: API کلید کی توثیق شامل کی گئی ★★★
# ==============================================================================

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

# ★★★ نیا: API کلید کی توثیق کا انحصار ★★★
API_KEY = os.getenv("API_KEY") # اپنی API کلید .env فائل سے حاصل کریں

async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """API کلید کی توثیق کرتا ہے۔"""
    if not API_KEY:
        # اگر سرور پر API کلید سیٹ نہیں ہے، تو سیکیورٹی کو غیر فعال سمجھیں (صرف ڈیولپمنٹ کے لیے)
        logger.warning("API_KEY ماحول کا متغیر سیٹ نہیں ہے۔ API کی توثیق غیر فعال ہے۔")
        return
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Key")

# DB انحصار
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API روٹس
# ★★★ اب تمام حساس روٹس `verify_api_key` پر منحصر ہیں ★★★
@app.get("/api/active-signals", response_class=JSONResponse, dependencies=[Depends(verify_api_key)])
async def get_active_signals(db: Session = Depends(get_db)):
    """تمام فعال سگنلز کو ڈیٹا بیس سے حاصل کرتا ہے۔"""
    try:
        signals = crud.get_all_active_signals_from_db(db)
        return [s.as_dict() for s in signals]
    except Exception as e:
        logger.error(f"فعال سگنلز حاصل کرنے میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

@app.post("/api/delete-signal/{signal_id}", response_class=JSONResponse)
async def delete_signal_endpoint(signal_id: str, password_data: dict, db: Session = Depends(get_db)):
    """ایک فعال سگنل کو دستی طور پر ڈیلیٹ کرتا ہے۔"""
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
    password = password_data.get("password")

    if not ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ایڈمن پاس ورڈ سرور پر کنفیگر نہیں ہے۔",
        )
    if not password or password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="غلط پاس ورڈ",
        )
    
    success = crud.delete_active_signal(db, signal_id)
    if success:
        await manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal_id}})
        return {"detail": f"سگنل {signal_id} کامیابی سے ڈیلیٹ ہو گیا۔"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"سگنل {signal_id} نہیں ملا۔"
        )

# ... (باقی کے فنکشنز جیسے start_background_tasks, startup_event, shutdown_event میں کوئی تبدیلی نہیں) ...

@app.get("/health", status_code=200)
async def health_check():
    """سروس کی صحت کی جانچ کرتا ہے۔ (یہ عوامی رہتا ہے)"""
    return {"status": "ok"}

@app.get("/api/history", response_class=JSONResponse, dependencies=[Depends(verify_api_key)])
async def get_history(db: Session = Depends(get_db)):
    """مکمل شدہ ٹریڈز کی تاریخ حاصل کرتا ہے۔"""
    try:
        trades = crud.get_completed_trades(db)
        return trades
    except Exception as e:
        logger.error(f"ہسٹری حاصل کرنے میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

@app.get("/api/news", response_class=JSONResponse, dependencies=[Depends(verify_api_key)])
async def get_news(db: Session = Depends(get_db)):
    """کیش شدہ خبریں حاصل کرتا ہے۔"""
    try:
        news = crud.get_cached_news(db)
        return news
    except Exception as e:
        logger.error(f"خبریں حاصل کرنے میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

# فرنٹ اینڈ کو ماؤنٹ کرنا آخر میں ہونا چاہیے
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

# نوٹ: فرنٹ اینڈ سے API کالز کو اپ ڈیٹ کرنے کی ضرورت ہوگی تاکہ وہ `X-API-KEY` ہیڈر بھیجیں۔
# چونکہ ہم براہ راست فرنٹ اینڈ فائلز کو اپ ڈیٹ نہیں کر سکتے، یہ ایک ضروری قدم ہوگا جسے
# فرنٹ اینڈ ڈیولپر کو کرنا ہوگا۔
         
