import os
import asyncio
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from contextlib import asynccontextmanager
from typing import List, Dict, Any

# Import our modules
from database_config import SessionLocal
from models import create_db_and_tables
import database_crud as crud
from hunter import hunt_for_signals_job, get_current_best_signal
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
from signal_tracker import get_active_signals
from key_manager import key_manager
from utils import test_api_connection, get_market_hours_status

# Initialize scheduler
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    print("--- Application Startup ---")
    
    # Create database tables
    try:
        create_db_and_tables()
        print("--- Database tables created/verified ---")
    except Exception as e:
        print(f"--- ERROR creating database tables: {e} ---")
    
    # Test API connection
    try:
        api_test = test_api_connection(key_manager)
        print(f"--- API Connection Test: {api_test} ---")
    except Exception as e:
        print(f"--- ERROR testing API connection: {e} ---")
    
    # Start background jobs
    try:
        # Hunt for signals every 5 minutes
        scheduler.add_job(
            hunt_for_signals_job,
            IntervalTrigger(minutes=5),
            args=[SessionLocal],
            misfire_grace_time=60,
            id="signal_hunter"
        )
        
        # Check active signals every minute
        scheduler.add_job(
            check_active_signals_job,
            IntervalTrigger(minutes=1),
            args=[SessionLocal],
            misfire_grace_time=30,
            id="signal_checker"
        )
        
        # Update economic calendar every 6 hours
        scheduler.add_job(
            update_economic_calendar_cache,
            IntervalTrigger(hours=6),
            misfire_grace_time=300,
            id="news_updater"
        )
        
        scheduler.start()
        print("--- Background scheduler started ---")
        
    except Exception as e:
        print(f"--- ERROR starting scheduler: {e} ---")
    
    yield
    
    # Shutdown
    print("--- Application Shutdown ---")
    try:
        scheduler.shutdown()
        print("--- Scheduler shutdown complete ---")
    except Exception as e:
        print(f"--- ERROR during scheduler shutdown: {e} ---")

# Create FastAPI app
app = FastAPI(lifespan=lifespan)

# Health check endpoint (required for Render.com)
@app.get("/health", status_code=200)
async def health_check():
    """Health check endpoint for deployment platforms"""
    try:
        # Test database connection
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        
        # Test API key manager
        key_status = key_manager.get_key_status()
        
        # Test market hours
        market_status = get_market_hours_status()
        
        return {
            "status": "ok",
            "database": "connected",
            "api_keys": key_status,
            "market_status": market_status,
            "scheduler": "running" if scheduler.running else "stopped"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# API Endpoints
@app.get("/api/active-signals", response_model=List[Dict[str, Any]])
async def get_live_signals_endpoint():
    """Get current active trading signals"""
    try:
        # Try to get from signal tracker first
        signals = get_active_signals()
        
        if not signals:
            # Fallback to getting the current best signal
            best_signal = get_current_best_signal()
            if best_signal:
                signals = [best_signal]
        
        return signals if signals else []
        
    except Exception as e:
        print(f"--- ERROR in get_live_signals_endpoint: {e} ---")
        raise HTTPException(status_code=500, detail="Error fetching active signals")

@app.get("/api/completed-trades")
async def get_completed_trades_endpoint():
    """Get completed trades history"""
    try:
        db = SessionLocal()
        trades = crud.get_completed_trades_from_db(db, limit=50)
        db.close()
        return trades
    except Exception as e:
        print(f"--- ERROR in get_completed_trades_endpoint: {e} ---")
        raise HTTPException(status_code=500, detail="Error fetching completed trades")

@app.get("/api/news")
async def get_news_endpoint():
    """Get economic news and events"""
    try:
        news = crud.get_news_from_cache()
        if not news:
            raise HTTPException(status_code=404, detail="Could not load news events.")
        return news
    except Exception as e:
        print(f"--- ERROR in get_news_endpoint: {e} ---")
        raise HTTPException(status_code=500, detail="Error fetching news")

@app.get("/api/historical-data")
async def get_historical_data_endpoint(
    symbol: str = Query("XAUUSD"),
    timeframe: str = Query("5m")
):
    """Get historical price data for charting"""
    try:
        from utils import fetch_historical_data_twelve_data
        
        historical_data = fetch_historical_data_twelve_data(symbol, timeframe, key_manager, days=7)
        
        if not historical_data:
            raise HTTPException(status_code=404, detail="Could not fetch historical data")
        
        return historical_data
        
    except Exception as e:
        print(f"--- ERROR in get_historical_data_endpoint: {e} ---")
        raise HTTPException(status_code=500, detail="Error fetching historical data")

@app.get("/api/manual-signal")
async def get_manual_signal_endpoint(
    symbol: str = Query("XAUUSD"),
    timeframe: str = Query("5m")
):
    """Manually generate a signal for testing purposes"""
    try:
        from hunter import manual_signal_hunt
        
        signal = await manual_signal_hunt(symbol, timeframe)
        
        if not signal:
            raise HTTPException(status_code=404, detail="Could not generate signal")
        
        return signal
        
    except Exception as e:
        print(f"--- ERROR in get_manual_signal_endpoint: {e} ---")
        raise HTTPException(status_code=500, detail="Error generating manual signal")

@app.get("/api/system-status")
async def get_system_status_endpoint():
    """Get system status and statistics"""
    try:
        # Get key manager status
        key_status = key_manager.get_key_status()
        
        # Get market status
        market_status = get_market_hours_status()
        
        # Get scheduler status
        scheduler_jobs = []
        if scheduler.running:
            for job in scheduler.get_jobs():
                scheduler_jobs.append({
                    "id": job.id,
                    "next_run": str(job.next_run_time) if job.next_run_time else "None"
                })
        
        return {
            "api_keys": key_status,
            "market_status": market_status,
            "scheduler": {
                "running": scheduler.running,
                "jobs": scheduler_jobs
            },
            "database": "connected"
        }
        
    except Exception as e:
        print(f"--- ERROR in get_system_status_endpoint: {e} ---")
        raise HTTPException(status_code=500, detail="Error getting system status")

# Mount static files (frontend)
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

print("--- FastAPI application initialized ---")
