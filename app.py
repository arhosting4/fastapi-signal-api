import sys
import os
import logging
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional

# --- CRITICAL FIX for Deployment ---
# Add the project root directory to the Python path.
# This allows Python to find modules in folders like 'src'.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# --- Corrected Imports for your file structure ---
from src.database import database_crud as crud, models
import database_config
import scheduler
import api_schemas

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create all database tables on startup
try:
    models.Base.metadata.create_all(bind=database_config.engine)
    logging.info("Database tables checked/created successfully.")
except Exception as e:
    logging.error(f"Error creating database tables: {e}")

app = FastAPI(
    title="ScalpMaster AI API", 
    version="1.3.0", # Version bump for the final fix
    description="A high-performance API for AI-driven scalping signals."
)

# --- Dependency ---
def get_db():
    db = database_config.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Scheduler Events ---
@app.on_event("startup")
def startup_event():
    scheduler.start_scheduler()
    logging.info("FastAPI application startup complete. Scheduler started.")

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown_scheduler()
    logging.info("FastAPI application shutdown. Scheduler stopped.")

# --- API Endpoints ---
@app.get("/health", status_code=200, tags=["System"])
def health_check():
    return {"status": "ok", "message": "API is running"}

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

# --- Static Files Mount ---
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
