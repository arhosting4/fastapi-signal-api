# filename: app.py

# --- Python Path Injection (اسے ہمیشہ رکھیں) ---
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import List, Dict, Any

# --- مرحلہ 2: صرف ڈیٹا بیس کے امپورٹس کو واپس لانا ---
from database_config import SessionLocal
from database_models import create_db_and_tables
import database_crud as crud
# ابھی بھی شیڈیولر اور اس کے جابز کو امپورٹ نہیں کرنا

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- Application Startup with Database ---")
    try:
        # ڈیٹا بیس اور ٹیبلز بنانے کی کوشش کریں
        create_db_and_tables()
        print("--- Database and tables verified/created successfully. ---")
    except Exception as e:
        # اگر ڈیٹا بیس میں کوئی مسئلہ ہے تو لاگز میں واضح طور پر نظر آئے گا
        print(f"--- CRITICAL ERROR DURING DB SETUP: {e} ---")
        # یہاں ایک خرابی سرور کو بوٹ ہونے سے روک سکتی ہے
    yield
    print("--- Application Shutdown ---")

app = FastAPI(lifespan=lifespan)

@app.get("/health", status_code=200)
async def health_check():
    print("--- Health check with DB connection was called successfully! ---")
    return {"status": "ok, server with database is running"}

# --- اب ہم API اینڈ پوائنٹس کو واپس لا سکتے ہیں جو ڈیٹا بیس استعمال کرتے ہیں ---
@app.get("/api/completed-trades")
async def get_completed_trades_endpoint():
    db = SessionLocal()
    try:
        # یہ چیک کرے گا کہ کیا ہم ڈیٹا بیس سے پڑھ سکتے ہیں
        trades = crud.get_completed_trades_from_db(db, limit=50)
        return trades
    finally:
        db.close()

@app.get("/api/news")
async def get_news_endpoint():
    # یہ چیک کرے گا کہ کیا ہم نیوز کیشے سے پڑھ سکتے ہیں
    news = crud.get_news_from_cache()
    if not news:
        raise HTTPException(status_code=404, detail="Could not load news events.")
    return news

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

print("--- app.py with database connection has been loaded by Python ---")
