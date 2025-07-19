import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from typing import Dict, Any

# ہمارے پروجیکٹ کے ایجنٹس
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from signal_tracker import get_live_signal, get_completed_signals
from sentinel import update_news_cache, get_news_analysis_for_symbol
from key_manager import API_KEYS

# --- FastAPI ایپ کی شروعات ---
app = FastAPI(title="ScalpMaster AI API")

# --- پس منظر کے کام (Background Jobs) ---
scheduler = AsyncIOScheduler()

# --- اہم تبدیلی: ایک نیا فنکشن جو اسٹارٹ اپ کے کاموں کو چلائے گا ---
async def run_initial_jobs():
    """
    یہ فنکشن پس منظر میں ابتدائی کاموں کو چلاتا ہے تاکہ سرور بلاک نہ ہو۔
    """
    print("Running initial jobs in the background...")
    # ہر کام کے درمیان تھوڑا وقفہ دیں تاکہ API کی حد سے بچا جا سکے
    await update_news_cache()
    await asyncio.sleep(5) # 5 سیکنڈ کا وقفہ
    await hunt_for_signals_job()
    await asyncio.sleep(5) # 5 سیکنڈ کا وقفہ
    await check_active_signals_job()
    print("Initial jobs completed.")

@app.on_event("startup")
async def startup_event():
    print("--- Server Startup ---")
    # یقینی بنائیں کہ API کلیدیں موجود ہیں
    if not API_KEYS:
        print("CRITICAL ERROR: No API keys found. Background jobs will not start.")
        return

    # --- اہم تبدیلی: لمبے کاموں کو براہ راست چلانے کی بجائے پس منظر میں بھیجیں ---
    # یہ سرور کو فوری طور پر شروع ہونے دے گا
    asyncio.create_task(run_initial_jobs())
    
    # اب، وقفے وقفے سے چلنے والے کاموں کو شیڈول کریں
    print("Scheduling background jobs...")
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=2), id="signal_hunter", name="Signal Hunter")
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=5), id="feedback_checker", name="Feedback Checker")
    scheduler.add_job(update_news_cache, IntervalTrigger(minutes=30), id="news_updater", name="News Updater")
    
    scheduler.start()
    print("--- Scheduler Started. Application is ready! ---")

@app.on_event("shutdown")
def shutdown_event():
    print("--- Server Shutdown ---")
    scheduler.shutdown()

# --- API اینڈ پوائنٹس ---

@app.get("/api/live-signal", response_model=Dict[str, Any])
async def get_current_signal():
    live_signal = get_live_signal()
    if not live_signal:
        raise HTTPException(status_code=404, detail="No live signal available.")
    return live_signal

@app.get("/api/history")
async def get_trade_history():
    return get_completed_signals()

@app.get("/api/news")
async def get_economic_news():
    pairs = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
    news_data = {pair: get_news_analysis_for_symbol(pair) for pair in pairs}
    return news_data

# ہیلتھ چیک اینڈ پوائنٹ (Render.com کے لیے ضروری)
@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

# --- اسٹیٹک فائلیں اور روٹ پیج ---
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
