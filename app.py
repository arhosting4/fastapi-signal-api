import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from typing import Dict, Any

# ہمارے پروجیکٹ کے ایجنٹس
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from signal_tracker import get_live_signal, get_completed_signals
from sentinel import update_news_cache, get_news_analysis_for_symbol # درست امپورٹ
from key_manager import API_KEYS # API کلیدوں کی تعداد چیک کرنے کے لیے

# --- FastAPI ایپ کی شروعات ---
app = FastAPI(title="ScalpMaster AI API")

# --- پس منظر کے کام (Background Jobs) ---
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    print("--- Server Startup ---")
    # یقینی بنائیں کہ API کلیدیں موجود ہیں
    if not API_KEYS:
        print("CRITICAL ERROR: No API keys found in environment variables. Background jobs will not start.")
        return

    # ایپ شروع ہوتے ہی ایک بار تمام جابز چلائیں
    print("Running initial jobs on startup...")
    await update_news_cache()
    await hunt_for_signals_job()
    await check_active_signals_job()
    
    # پھر انہیں وقفے وقفے سے چلانے کے لیے شیڈول کریں
    print("Scheduling background jobs...")
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=2), id="signal_hunter", name="Signal Hunter")
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=5), id="feedback_checker", name="Feedback Checker")
    scheduler.add_job(update_news_cache, IntervalTrigger(minutes=30), id="news_updater", name="News Updater")
    
    scheduler.start()
    print("--- Scheduler Started ---")

@app.on_event("shutdown")
def shutdown_event():
    print("--- Server Shutdown ---")
    scheduler.shutdown()

# --- API اینڈ پوائنٹس ---

@app.get("/api/live-signal", response_model=Dict[str, Any])
async def get_current_signal():
    """
    ویب سائٹ کے لیے موجودہ لائیو سگنل فراہم کرتا ہے۔
    """
    live_signal = get_live_signal()
    if not live_signal:
        raise HTTPException(status_code=404, detail="No live signal available.")
    return live_signal

@app.get("/api/history")
async def get_trade_history():
    """
    مکمل شدہ ٹریڈز کی تاریخ فراہم کرتا ہے۔
    """
    return get_completed_signals()

@app.get("/api/news")
async def get_economic_news():
    """
    تمام اہم کرنسیوں کے لیے خبروں کا تجزیہ فراہم کرتا ہے۔
    """
    # تمام اہم جوڑوں کے لیے خبروں کا تجزیہ حاصل کریں
    pairs = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
    news_data = {pair: get_news_analysis_for_symbol(pair) for pair in pairs}
    return news_data

# --- اسٹیٹک فائلیں اور روٹ پیج ---
# یہ لائن 'frontend' فولڈر میں موجود تمام فائلوں کو پیش کرے گی
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

# ہیلتھ چیک اینڈ پوائنٹ (Render.com کے لیے ضروری)
@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

