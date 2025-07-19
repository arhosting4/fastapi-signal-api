import os
import traceback
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from typing import Dict, Any

# ہمارے پروجیکٹ کے ماڈیولز
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
from signal_tracker import get_live_signal, add_active_signal

app = FastAPI(title="ScalpMaster AI - Hunter Edition v4 (Fully Transparent)")

scheduler = AsyncIOScheduler(timezone="UTC")

@app.on_event("startup")
async def startup_event():
    # ... (یہ فنکشن ویسے ہی رہے گا) ...
    print("--- ScalpMaster AI Engine: Initializing Startup Sequence ---")
    await update_economic_calendar_cache()
    scheduler.add_job(hunt_for_signals_job, 'interval', minutes=10, id="hunter_job")
    scheduler.add_job(check_active_signals_job, 'interval', minutes=10, seconds=5, id="checker_job")
    scheduler.add_job(update_economic_calendar_cache, 'interval', hours=12, id="news_updater_job")
    scheduler.start()
    print("--- ScalpMaster AI Hunter Engine Started Successfully ---")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    print("--- ScalpMaster AI Hunter Engine Shut Down ---")

@app.get("/health", status_code=200, tags=["System"])
async def health_check():
    return {"status": "ok", "message": "ScalpMaster AI Hunter is running."}

@app.get("/api/get_live_signal", tags=["AI Hunter"])
async def get_current_signal():
    # ... (یہ فنکشن ویسے ہی رہے گا) ...
    try:
        live_signal = get_live_signal()
        if live_signal and live_signal.get("signal") in ["buy", "sell"]:
            add_active_signal(live_signal)
        return live_signal
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching live signal: {e}")

@app.get("/api/get_trade_history", tags=["Performance"])
async def get_trade_history():
    # ... (یہ فنکشن ویسے ہی رہے گا) ...
    history_file = "data/trade_history.json"
    try:
        if os.path.exists(history_file):
            with open(history_file, "r") as f:
                history_data = json.load(f)
                history_data.reverse()
                return JSONResponse(content=history_data)
        else:
            return JSONResponse(content=[])
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error reading trade history: {e}")

# --- نیا نیوز API اینڈ پوائنٹ ---
@app.get("/api/get_news_events", tags=["Fundamental Analysis"])
async def get_news_events():
    """
    کیشے شدہ ہائی امپیکٹ نیوز ایونٹس کو JSON فائل سے پڑھ کر واپس کرتا ہے۔
    """
    news_cache_file = "data/news_cache.json"
    try:
        if os.path.exists(news_cache_file):
            with open(news_cache_file, "r") as f:
                news_data = json.load(f)
                # خبروں کو تاریخ کے لحاظ سے ترتیب دیں
                news_data.sort(key=lambda x: x.get('date', ''))
                return JSONResponse(content=news_data)
        else:
            return JSONResponse(content=[])
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error reading news cache: {e}")

# اسٹیٹک فائلوں کو پیش کرنے کے لیے
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
    
