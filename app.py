import logging
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

# --- Local Imports ---
from .database import database_crud as crud
from .database.database_config import SessionLocal, engine, Base
from .database import models
from .scheduler import scheduler, start_scheduler, shutdown_scheduler
from .api_schemas import TradeHistory, ActiveSignal, News, Summary

# Create all database tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ScalpMaster AI API", version="1.0.0")

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Scheduler Events ---
@app.on_event("startup")
def startup_event():
    start_scheduler()
    logging.info("FastAPI application startup complete. Scheduler started.")

@app.on_event("shutdown")
def shutdown_event():
    shutdown_scheduler()
    logging.info("FastAPI application shutdown. Scheduler stopped.")

# --- API Endpoints ---

@app.get("/health", status_code=200)
def health_check():
    """Endpoint to check the health of the application."""
    return {"status": "ok"}

@app.get("/api/live-signals", response_model=List[ActiveSignal])
def get_live_signals(db: Session = Depends(get_db)):
    """Provides a list of all currently active trading signals."""
    signals = crud.get_all_active_signals(db)
    return signals

@app.get("/api/history", response_model=List[TradeHistory])
def get_trade_history(limit: int = 100, db: Session = Depends(get_db)):
    """Provides a history of recently completed trades."""
    trades = crud.get_completed_trades(db, limit=limit)
    return trades

@app.get("/api/news", response_model=Optional[News])
def get_latest_news(db: Session = Depends(get_db)):
    """Provides the latest cached market news."""
    news = crud.get_cached_news(db)
    if not news:
        return {"message": "No high-impact news available at the moment."}
    return news

@app.get("/api/summary", response_model=Summary)
def get_summary_data(db: Session = Depends(get_db)):
    """Calculates and provides summary data like Win Rate and P/L."""
    summary = crud.get_summary_stats(db)
    return summary

# --- Static Files Mount ---
# This must be the last part of the app definition
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

