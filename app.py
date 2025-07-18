import os
import traceback
import asyncio
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

# --- اہم تبدیلی: utils.py سے امپورٹ کریں ---
from utils import fetch_twelve_data_ohlc
from feedback_checker import check_active_signals_job
from fusion_engine import generate_final_signal
from signal_tracker import get_active_signal_for_timeframe, add_active_signal

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
app = FastAPI(title="ScalpMaster AI API")

price_cache = {}
CACHE_DURATION_SECONDS = 20

scheduler = AsyncIOScheduler(timezone="UTC")

@app.on_event("startup")
async def startup_event():
    if not TWELVE_DATA_API_KEY:
        print("CRITICAL WARNING: TWELVE_DATA_API_KEY is not set.")
    scheduler.add_job(check_active_signals_job, 'interval', seconds=60, id="signal_check_job")
    scheduler.start()
    print("APScheduler started.")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    print("APScheduler has been shut down.")

# (fetch_twelve_data_ohlc فنکشن یہاں سے ہٹا دیا گیا ہے)

@app.get("/health", status_code=200, tags=["System"])
async def health_check():
    return {"status": "ok", "message": "ScalpMaster AI is running."}

@app.get("/api/price", tags=["Real-time Data"])
async def get_realtime_price(symbol: str = Query("XAU/USD")):
    now = datetime.utcnow()
    if symbol in price_cache:
        cached_price, cache_time = price_cache[symbol]
        if now - cache_time < timedelta(seconds=CACHE_DURATION_SECONDS):
            print(f"CACHE HIT: Returning cached price for {symbol}: {cached_price}")
            return {"symbol": symbol, "price": cached_price, "source": "cache"}
    print(f"CACHE MISS: Fetching new price for {symbol} from Twelve Data.")
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

@app.get("/api/signal", tags=["AI Signals"])
async def get_signal(symbol: str = Query("XAU/USD"), timeframe: str = Query("5m")):
    try:
        active_signal = get_active_signal_for_timeframe(symbol, timeframe)
        if active_signal:
            print(f"Returning existing active signal {active_signal.get('id')}.")
            candles = await fetch_twelve_data_ohlc(symbol, timeframe)
            active_signal['candles'] = candles
            return active_signal
        print(f"No active signal found. Generating new one.")
        candles = await fetch_twelve_data_ohlc(symbol, timeframe)
        if not candles or len(candles) < 50: # اب ہمیں بڑے ٹائم فریم کے لیے بھی ڈیٹا چاہیے
            raise HTTPException(status_code=404, detail="Not enough historical data for a new signal.")
        signal_result = await generate_final_signal(symbol, candles, timeframe)
        if signal_result.get("signal") in ["buy", "sell"]:
            add_active_signal(signal_result)
        return signal_result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
        
