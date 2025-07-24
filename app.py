import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager
from typing import List # List کو امپورٹ کرنا

# ===================================================================
# THIS IS THE CORRECTED VERSION WITH FIXED IMPORTS FOR YOUR FLAT STRUCTURE
# ===================================================================

# درست امپورٹس (بغیر 'src' کے)
import database_crud as crud
from database_config import SessionLocal, engine
import models
import api_schemas as schemas
import hunter
import feedback_checker
import sentinel

# لاگنگ کی ترتیب
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ڈیٹا بیس ٹیبلز بنانا
try:
    models.Base.metadata.create_all(bind=engine)
    logging.info("Database tables checked/created successfully.")
except Exception as e:
    logging.critical(f"FATAL: Could not create database tables: {e}", exc_info=True)

# شیڈولر کی ترتیب
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # اسٹارٹ اپ پر چلنے والا کوڈ
    logging.info("Application startup...")
    try:
        scheduler.add_job(hunter.hunt_for_signals, 'interval', minutes=5, id='hunt_for_signals_job')
        scheduler.add_job(feedback_checker.check_active_signals, 'interval', minutes=1, id='check_active_signals_job')
        scheduler.add_job(sentinel.update_economic_calendar_cache, 'interval', hours=4, id='update_economic_calendar_cache_job')
        scheduler.start()
        logging.info("Scheduler started with jobs.")
    except Exception as e:
        logging.error(f"Failed to start scheduler: {e}", exc_info=True)
    yield
    # شٹ ڈاؤن پر چلنے والا کوڈ
    logging.info("Application shutdown...")
    scheduler.shutdown()

app = FastAPI(title="ScalpMaster AI API", lifespan=lifespan)

# --- API Endpoints ---

@app.get("/api/summary", response_model=schemas.Summary)
def get_summary():
    """
    Provides summary stats like win rate and P&L.
    This endpoint is now robust and directly returns the correct schema.
    """
    db = SessionLocal()
    try:
        stats = crud.get_summary_stats(db)
        return schemas.Summary(win_rate=stats.get("win_rate", 0.0), pnl=stats.get("pnl", 0.0))
    except Exception as e:
        logging.error(f"Error in /api/summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not fetch summary statistics.")
    finally:
        db.close()

@app.get("/api/live-signals", response_model=List[schemas.Signal])
def get_live_signals():
    """
    Provides a list of active trading signals.
    This endpoint is now robust and directly returns the correct schema.
    """
    db = SessionLocal()
    try:
        active_signals = crud.get_all_active_signals(db)
        return [schemas.Signal.from_orm(signal) for signal in active_signals]
    except Exception as e:
        logging.error(f"Error in /api/live-signals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not fetch live signals.")
    finally:
        db.close()

@app.get("/api/history", response_model=List[schemas.Trade])
def get_history():
    """Provides a list of completed trades."""
    db = SessionLocal()
    try:
        trade_history = crud.get_trade_history(db)
        return [schemas.Trade.from_orm(trade) for trade in trade_history]
    except Exception as e:
        logging.error(f"Error in /api/history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not fetch trade history.")
    finally:
        db.close()

@app.get("/api/news", response_model=schemas.NewsResponse)
def get_news():
    """Provides cached market news."""
    db = SessionLocal()
    try:
        news_cache = crud.get_cached_news(db)
        if news_cache and news_cache.content:
            return news_cache.content
        return {"message": "No high-impact news available.", "data": []}
    except Exception as e:
        logging.error(f"Error in /api/news: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not fetch news.")
    finally:
        db.close()

@app.get("/health")
def health_check():
    return {"status": "ok"}

# --- Static Files and Root Path ---
# یہ یقینی بناتا ہے کہ فرنٹ اینڈ فائلیں صحیح طریقے سے پیش کی جائیں

FRONTEND_DIR = Path(__file__).parent / "frontend"

# روٹ پاتھ (/) پر index.html دکھانا
@app.get("/", response_class=FileResponse)
async def read_index():
    return FileResponse(FRONTEND_DIR / "index.html")

# باقی تمام فرنٹ اینڈ فائلوں کو پیش کرنا
app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="static")
    
