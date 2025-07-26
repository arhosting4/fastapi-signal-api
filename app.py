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
from models import SessionLocal

# لاگنگ کی ترتیب gunicorn_conf.py میں ہے
logger = logging.getLogger(__name__)

app = FastAPI(title="ScalpMaster AI API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# DB انحصار
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# WebSocket اینڈ پوائنٹ
@app.websocket("/ws/live-signals")
async def websocket_endpoint(websocket: WebSocket):
    from websocket_manager import manager
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("کلائنٹ نے WebSocket کنکشن بند کر دیا۔")

# API روٹس
@app.get("/health", status_code=200)
async def health_check():
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
        if not news or not news.get("articles"):
            return JSONResponse(status_code=404, content={"message": "کوئی خبر نہیں ملی۔"})
        return news
    except Exception as e:
        logger.error(f"خبریں حاصل کرنے میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

# پس منظر کے کاموں کو شروع کرنے والا فنکشن
async def startup_background_tasks():
    logger.info("پس منظر کے کاموں کی ترتیب شروع کی جا رہی ہے...")
    
    from price_stream import start_price_websocket
    from hunter import hunt_for_signals_job
    from feedback_checker import check_active_signals_job
    from sentinel import update_economic_calendar_cache
    from models import create_db_and_tables
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    create_db_and_tables()
    asyncio.create_task(start_price_websocket())
    await update_economic_calendar_cache()

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=5), id="hunt_for_signals")
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), id="check_active_signals")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="update_news")
    scheduler.start()
    
    logger.info("★★★ پس منظر کے تمام کام اور شیڈیولر کامیابی سے شروع ہو گئے۔ ★★★")
    
    while True:
        await asyncio.sleep(3600)

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# ★★★ حتمی اور درست تبدیلی: اصل کوڈ کو واپس شامل کرنا ★★★
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# سٹیٹک فائلز
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
    
