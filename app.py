import os
import traceback
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

# ہمارے پروجیکٹ کے ماڈیولز
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache # sentinel سے نیا فنکشن
from signal_tracker import get_live_signal, add_active_signal

app = FastAPI(title="ScalpMaster AI - Hunter Edition")

price_cache = {}
CACHE_DURATION_SECONDS = 30

scheduler = AsyncIOScheduler(timezone="UTC")

@app.on_event("startup")
async def startup_event():
    """سرور شروع ہونے پر پس منظر کی جابز کو شروع کرتا ہے۔"""
    # سرور شروع ہوتے ہی ایک بار نیوز کیشے کو فوری اپ ڈیٹ کریں
    await update_economic_calendar_cache()

    # 1. سگنل ہنٹر جاب (ہر 60 سیکنڈ)
    scheduler.add_job(hunt_for_signals_job, 'interval', seconds=60, id="hunter_job")
    
    # 2. TP/SL نگران جاب (ہر 65 سیکنڈ)
    scheduler.add_job(check_active_signals_job, 'interval', seconds=65, id="checker_job")
    
    # 3. نیوز کیشے اپڈیٹر (ہر 12 گھنٹے)
    scheduler.add_job(update_economic_calendar_cache, 'interval', hours=12, id="news_updater_job")
    
    scheduler.start()
    print("--- ScalpMaster AI Hunter Engine Started ---")
    print("Scheduler is running: Hunter (1m), Checker (1m), and News Updater (12h).")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    print("--- ScalpMaster AI Hunter Engine Shut Down ---")

@app.get("/health", status_code=200, tags=["System"])
async def health_check():
    return {"status": "ok", "message": "ScalpMaster AI Hunter is running."}

@app.get("/api/get_live_signal", tags=["AI Hunter"])
async def get_current_signal():
    """پس منظر میں AI ہنٹر کے ذریعے پائے جانے والے بہترین لائیو سگنل کو فوری طور پر واپس کرتا ہے۔"""
    try:
        live_signal = get_live_signal()
        if live_signal and live_signal.get("signal") in ["buy", "sell"]:
            add_active_signal(live_signal)
        return live_signal
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching live signal: {e}")

@app.get("/api/price", tags=["Real-time Data"])
async def get_realtime_price(symbol: str = Query("XAU/USD")):
    """چارٹ کے لیے قیمت حاصل کرتا ہے (کیشنگ کے ساتھ)۔"""
    now = datetime.utcnow()
    if symbol in price_cache:
        cached_price, cache_time = price_cache[symbol]
        if now - cache_time < timedelta(seconds=CACHE_DURATION_SECONDS):
            return {"symbol": symbol, "price": cached_price, "source": "cache"}
    
    TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
    if not TWELVE_DATA_API_KEY:
        raise HTTPException(status_code=500, detail="API key is not configured.")
    
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_DATA_API_KEY}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "price" in data:
            new_price = float(data["price"])
            price_cache[symbol] = (new_price, now)
            return {"symbol": symbol, "price": new_price, "source": "api"}
        else:
            raise HTTPException(status_code=404, detail="Price not available for the symbol.")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch real-time price: {str(e)}")

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
