# app.py - (اس فائل میں کوئی تبدیلی نہیں کرنی، یہ بالکل ٹھیک ہے)
import sys
import os
import logging
from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

from src.database import database_crud as crud, models
import database_config, scheduler, api_schemas

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
try:
    models.Base.metadata.create_all(bind=database_config.engine)
    logging.info("Database tables checked/created successfully.")
except Exception as e:
    logging.error(f"Error creating database tables: {e}")

app = FastAPI(title="ScalpMaster AI API")

def get_db():
    db = database_config.SessionLocal()
    try: yield db
    finally: db.close()

@app.on_event("startup")
def startup_event(): scheduler.start_scheduler()
@app.on_event("shutdown")
def shutdown_event(): scheduler.shutdown_scheduler()

@app.get("/health", status_code=200)
def health_check(): return {"status": "ok"}
@app.get("/api/live-signals", response_model=List[api_schemas.ActiveSignal])
def get_live_signals(db: Session = Depends(get_db)): return crud.get_all_active_signals(db)
@app.get("/api/history", response_model=List[api_schemas.TradeHistory])
def get_trade_history(limit: int = 100, db: Session = Depends(get_db)): return crud.get_completed_trades(db, limit=limit)
@app.get("/api/news", response_model=Optional[api_schemas.News])
def get_latest_news(db: Session = Depends(get_db)):
    news = crud.get_cached_news(db)
    if not news or not news.get('data'): return {"message": "No high-impact news available."}
    return news
@app.get("/api/summary", response_model=api_schemas.Summary)
def get_summary_data(db: Session = Depends(get_db)): return crud.get_summary_stats(db)

@app.get("/{page_name:path}", response_class=HTMLResponse)
async def serve_frontend(page_name: str):
    if page_name == "" or not page_name.endswith(".html"): page_name = "index.html"
    file_path = FRONTEND_DIR / page_name
    allowed_files = ["index.html", "history.html", "news.html"]
    if page_name not in allowed_files: file_path = FRONTEND_DIR / "index.html"
    if file_path.exists():
        with open(file_path) as f: return HTMLResponse(content=f.read(), status_code=200)
    else: return HTMLResponse(content="<h1>404 - Not Found</h1>", status_code=404)
        
