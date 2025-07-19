from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import uvicorn
import os
import atexit

# Import our modules
from database_config import get_db
from models import create_db_and_tables
from database_crud import get_all_active_trades_from_db, get_completed_trades_from_db, get_news_from_cache
from signal_tracker import get_active_signals_from_json
from hunter import hunt_for_signals_job
from feedback_checker import check_feedback_job
from sentinel import update_news_cache_job

# Initialize FastAPI app
app = FastAPI(title="ScalpMaster AI", description="Advanced Trading Signal Generator", version="1.0.0")

# Mount static files (for serving HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="."), name="static")

# Initialize database
print("--- Initializing database... ---")
create_db_and_tables()
print("--- Database initialization completed ---")

# Initialize scheduler
scheduler = BackgroundScheduler()

# Schedule jobs
print("--- Setting up scheduled jobs... ---")

# Hunter job: Every 5 minutes
scheduler.add_job(
    func=hunt_for_signals_job,
    trigger=IntervalTrigger(minutes=5),
    id='hunter_job',
    name='Hunt for trading signals',
    replace_existing=True
)

# Feedback checker job: Every 1 minute
scheduler.add_job(
    func=check_feedback_job,
    trigger=IntervalTrigger(minutes=1),
    id='feedback_job',
    name='Check trade feedback',
    replace_existing=True
)

# News update job: Every 30 minutes
scheduler.add_job(
    func=update_news_cache_job,
    trigger=IntervalTrigger(minutes=30),
    id='news_job',
    name='Update news cache',
    replace_existing=True
)

# Start scheduler
scheduler.start()
print("--- Background jobs scheduled and started ---")

# Shut down scheduler when app exits
atexit.register(lambda: scheduler.shutdown())

# API Routes
@app.get("/")
async def read_root():
    """Serve the main dashboard"""
    return FileResponse('index.html')

@app.get("/index.html")
async def serve_index():
    """Serve the main dashboard"""
    return FileResponse('index.html')

@app.get("/history.html")
async def serve_history():
    """Serve the trade history page"""
    return FileResponse('history.html')

@app.get("/news.html")
async def serve_news():
    """Serve the market news page"""
    return FileResponse('news.html')

@app.get("/api/active-signals")
async def get_active_signals():
    """Get all active trading signals"""
    try:
        # First try to get from JSON file (faster)
        signals = get_active_signals_from_json()
        if signals:
            return signals
        
        # Fallback to database
        db = next(get_db())
        db_signals = get_all_active_trades_from_db(db)
        
        # Convert database objects to dictionaries
        signals_list = []
        for signal in db_signals:
            signals_list.append({
                "id": signal.id,
                "symbol": signal.symbol,
                "signal": signal.signal,
                "timeframe": signal.timeframe,
                "price": signal.entry_price,
                "tp": signal.tp,
                "sl": signal.sl,
                "confidence": signal.confidence,
                "reason": signal.reason,
                "tier": signal.tier,
                "entry_time": signal.entry_time.isoformat() if signal.entry_time else None
            })
        
        return signals_list
        
    except Exception as e:
        print(f"--- ERROR in get_active_signals: {e} ---")
        return []

@app.get("/api/completed-trades")
async def get_completed_trades(db: Session = Depends(get_db)):
    """Get completed trades history"""
    try:
        trades = get_completed_trades_from_db(db, limit=50)
        
        # Convert database objects to dictionaries
        trades_list = []
        for trade in trades:
            trades_list.append({
                "id": trade.id,
                "symbol": trade.symbol,
                "signal": trade.signal,
                "entry_price": trade.entry_price,
                "close_price": trade.close_price,
                "tp": trade.tp,
                "sl": trade.sl,
                "outcome": trade.outcome,
                "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
                "close_time": trade.close_time.isoformat() if trade.close_time else None
            })
        
        return trades_list
        
    except Exception as e:
        print(f"--- ERROR in get_completed_trades: {e} ---")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/news")
async def get_market_news():
    """Get latest market news"""
    try:
        news = get_news_from_cache()
        return news
        
    except Exception as e:
        print(f"--- ERROR in get_market_news: {e} ---")
        return []

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "scheduler_running": scheduler.running,
        "jobs": [job.id for job in scheduler.get_jobs()]
    }

# Run the application
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
                               
