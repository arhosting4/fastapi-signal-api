import os
import traceback
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

# ہمارے پروجیکٹ کے ماڈیولز
from hunter import hunt_for_signals_job # نیا ہنٹر
from feedback_checker import check_active_signals_job # پرانا نگران
from signal_tracker import get_live_signal, add_active_signal # ٹریکر سے نئے فنکشنز

app = FastAPI(title="ScalpMaster AI - Hunter Edition")

# قیمت کی کیشنگ اب بھی چارٹ کے لیے مفید ہے
price_cache = {}
CACHE_DURATION_SECONDS = 30

scheduler = AsyncIOScheduler(timezone="UTC")

@app.on_event("startup")
async def startup_event():
    """سرور شروع ہونے پر پس منظر کی جابز کو شروع کرتا ہے۔"""
    # 1. سگنل ہنٹر جاب (ہر 60 سیکنڈ میں نئے مواقع تلاش کرتی ہے)
    scheduler.add_job(hunt_for_signals_job, 'interval', seconds=60, id="hunter_job")
    
    # 2. TP/SL نگران جاب (ہر 65 سیکنڈ میں، تاکہ ہنٹر کے ساتھ ٹکراؤ نہ ہو)
    scheduler.add_job(check_active_signals_job, 'interval', seconds=65, id="checker_job")
    
    scheduler.start()
    print("--- ScalpMaster AI Hunter Engine Started ---")
    print("Scheduler is running 'hunt_for_signals_job' and 'check_active_signals_job'.")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    print("--- ScalpMaster AI Hunter Engine Shut Down ---")

@app.get("/health", status_code=200, tags=["System"])
async def health_check():
    return {"status": "ok", "message": "ScalpMaster AI Hunter is running."}

# --- نیا مرکزی اینڈ پوائنٹ ---
@app.get("/api/get_live_signal", tags=["AI Hunter"])
async def get_current_signal():
    """
    پس منظر میں AI ہنٹر کے ذریعے پائے جانے والے بہترین لائیو سگنل کو فوری طور پر واپس کرتا ہے۔
    یہ کوئی نئی API کال نہیں کرتا۔
    """
    try:
        live_signal = get_live_signal()
        # جب صارف سگنل دیکھتا ہے، تب ہی اسے فعال ٹریکر میں شامل کریں
        if live_signal and live_signal.get("signal") in ["buy", "sell"]:
            # یہ یقینی بناتا ہے کہ TP/SL کی نگرانی صرف تب شروع ہو جب سگنل دیکھا گیا ہو
            add_active_signal(live_signal)
        return live_signal
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching live signal: {e}")

# (پرانا /api/signal اینڈ پوائنٹ ہٹا دیا گیا ہے)

# چارٹ کو زندہ رکھنے کے لیے یہ اینڈ پوائنٹ اب بھی موجود ہے
@app.get("/api/price", tags=["Real-time Data"])
async def get_realtime_price(symbol: str = Query("XAU/USD")):
    # (یہ فنکشن ویسے ہی رہے گا جیسا پچھلی بار تھا)
    now = datetime.utcnow()
    if symbol in price_cache:
        cached_price, cache_time = price_cache[symbol]
        if now - cache_time < timedelta(seconds=CACHE_DURATION_SECONDS):
            return {"symbol": symbol, "price": cached_price, "source": "cache"}
    
    # (باقی کوڈ ویسے ہی)
    # ...

# اسٹیٹک فائلوں کو پیش کریں
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
