import sys
import os
import logging
from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path

# --- Basic Setup ---
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

# --- Imports (No Changes) ---
from src.database import database_crud as crud, models
import database_config
import scheduler
import api_schemas

# --- Logging and DB Setup (No Changes) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
try:
    models.Base.metadata.create_all(bind=database_config.engine)
    logging.info("Database tables checked/created successfully.")
except Exception as e:
    logging.error(f"Error creating database tables: {e}")

app = FastAPI(title="ScalpMaster AI API")

# --- Dependency (No Changes) ---
def get_db():
    db = database_config.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Scheduler Events (No Changes) ---
@app.on_event("startup")
def startup_event():
    scheduler.start_scheduler()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown_scheduler()

# --- API Endpoints (No Changes) ---
@app.get("/health", status_code=200, tags=["System"])
def health_check():
    return {"status": "ok"}

@app.get("/api/live-signals", response_model=List[api_schemas.ActiveSignal], tags=["Data"])
def get_live_signals(db: Session = Depends(get_db)):
    return crud.get_all_active_signals(db)

@app.get("/api/history", response_model=List[api_schemas.TradeHistory], tags=["Data"])
def get_trade_history(limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_completed_trades(db, limit=limit)

@app.get("/api/news", response_model=Optional[api_schemas.News], tags=["Data"])
def get_latest_news(db: Session = Depends(get_db)):
    news = crud.get_cached_news(db)
    if not news or not news.get('data'):
        return {"message": "No high-impact news available at the moment."}
    return news

@app.get("/api/summary", response_model=api_schemas.Summary, tags=["Data"])
def get_summary_data(db: Session = Depends(get_db)):
    return crud.get_summary_stats(db)

# --- Static File Serving (THE FINAL AND CORRECTED VERSION) ---

# This function will serve index.html, history.html, and news.html
@app.get("/{page_name:path}", response_class=HTMLResponse)
async def serve_frontend(page_name: str):
    # If the path is empty (root URL), serve index.html
    if page_name == "":
        page_name = "index.html"

    file_path = FRONTEND_DIR / page_name
    
    # Security check: ensure the file is one of the allowed HTML files
    allowed_files = ["index.html", "history.html", "news.html"]
    if page_name not in allowed_files:
        # If requested file is not allowed, default to index.html
        file_path = FRONTEND_DIR / "index.html"

    if file_path.exists():
        with open(file_path) as f:
            return HTMLResponse(content=f.read(), status_code=200)
    else:
        # If for some reason index.html is also missing, return a simple error
        return HTMLResponse(content="<h1>404 - Not Found</h1><p>Frontend file not found.</p>", status_code=404)

