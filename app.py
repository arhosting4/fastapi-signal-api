import logging
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional

from .database import database_crud as crud, models
from .database.database_config import SessionLocal, engine
from .scheduler import start_scheduler, shutdown_scheduler
from .api_schemas import TradeHistory, ActiveSignal, News, Summary

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ScalpMaster AI API", version="1.0.0")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup_event():
    start_scheduler()
    logging.info("FastAPI application startup complete. Scheduler started.")

@app.on_event("shutdown")
def shutdown_event():
    shutdown_scheduler()
    logging.info("FastAPI application shutdown. Scheduler stopped.")

@app.get("/health", status_code=200, tags=["System"])
def health_check():
    return {"status": "ok"}

@app.get("/api/live-signals", response_model=List[ActiveSignal], tags=["Data"])
def get_live_signals(db: Session = Depends(get_db)):
    return crud.get_all_active_signals(db)

@app.get("/api/history", response_model=List[TradeHistory], tags=["Data"])
def get_trade_history(limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_completed_trades(db, limit=limit)

@app.get("/api/news", response_model=Optional[News], tags=["Data"])
def get_latest_news(db: Session = Depends(get_db)):
    news = crud.get_cached_news(db)
    if not news:
        return {"message": "No high-impact news available at the moment."}
    return news

@app.get("/api/summary", response_model=Summary, tags=["Data"])
def get_summary_data(db: Session = Depends(get_db)):
    return crud.get_summary_stats(db)

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
