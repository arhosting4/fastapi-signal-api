# app.py

import os
import asyncio
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from typing import List, Optional

# --- ڈیٹا بیس کے لیے امپورٹس ---
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
# --- تبدیلی: اب SessionLocal یہاں سے امپورٹ ہوگا ---
from src.database.models import create_db_and_tables, SessionLocal
import database_crud as crud
from src.database.models import CompletedTrade as CompletedTradeModel

# .env فائل سے ویری ایبلز لوڈ کریں
load_dotenv()

# FastAPI ایپ کی شروعات
app = FastAPI(title="ScalpMaster AI API")

# --- ڈیٹا بیس سیشن حاصل کرنے کا انحصار ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- پس منظر کے کاموں کے لیے شیڈیولر ---
scheduler = BackgroundScheduler()

# --- ہیلتھ چیک اینڈ پوائنٹ ---
@app.get("/health", status_code=200)
async def health_check(db: Session = Depends(get_db)):
    db_status = "ok"
    try:
        crud.get_completed_trades(db, limit=1) 
    except Exception:
        db_status = "error"
    return {"status": "ok", "database_status": db_status}

# --- API اینڈ پوائنٹس ---
@app.get("/api/live-signal", response_class=JSONResponse)
async def get_live_signal():
    return {"reason": "Database integration in progress..."}

@app.get("/api/history", response_class=JSONResponse)
async def get_history(db: Session = Depends(get_db)):
    try:
        trades = crud.get_completed_trades(db, limit=100)
        return [
            {
                "symbol": trade.symbol,
                "timeframe": trade.timeframe,
                "signal_type": trade.signal_type,
                "entry_price": trade.entry_price,
                "outcome": trade.outcome,
                "closed_at": trade.closed_at.strftime("%Y-%m-%d %H:%M:%S")
            }
            for trade in trades
        ]
    except Exception as e:
        print(f"--- API ERROR in /api/history: {e} ---")
        raise HTTPException(status_code=500, detail="Could not fetch trade history from database.")

@app.get("/api/news", response_class=JSONResponse)
async def get_news():
    return {}

# --- ایپ کے شروع اور بند ہونے پر ایونٹس ---
@app.on_event("startup")
async def startup_event():
    print("--- ScalpMaster AI Server is starting up... ---")
    create_db_and_tables()
    print("--- Scheduler is paused during database setup. ---")

@app.on_event("shutdown")
async def shutdown_event():
    print("--- ScalpMaster AI Server is shutting down... ---")
    if scheduler.running:
        scheduler.shutdown()

# --- اسٹیٹک فائلیں اور روٹ پیج (سب سے آخر میں) ---
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
