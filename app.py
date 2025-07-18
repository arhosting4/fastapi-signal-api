import os
import traceback
import asyncio
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pandas as pd
from datetime import datetime, timedelta # وقت کے لیے timedelta امپورٹ کریں

# ہمارے اپنے ماڈیولز
from feedback_checker import check_active_signals_job
from fusion_engine import generate_final_signal
from signal_tracker import get_active_signal_for_timeframe, add_active_signal

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

app = FastAPI(title="ScalpMaster AI API")

# --- ذہین کیشنگ سسٹم ---
# یہ ڈکشنری قیمتوں کو سرور کی میموری میں محفوظ کرے گی
# {'SYMBOL': (price, timestamp)}
price_cache = {}
CACHE_DURATION_SECONDS = 20 # 20 سیکنڈ کے لیے قیمت کو کیش کریں

scheduler = AsyncIOScheduler(timezone="UTC")

@app.on_event("startup")
async def startup_event():
    if not TWELVE_DATA_API_KEY:
        print("CRITICAL WARNING: TWELVE_DATA_API_KEY is not set.")
    scheduler.add_job(check_active_signals_job, 'interval', seconds=60, id="signal_check_job")
    scheduler.start()
    print("APScheduler started. Signal checker is running every 60 seconds.")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    print("APScheduler has been shut down.")

async def fetch_twelve_data_ohlc(symbol: str, timeframe: str, output_size: int = 100):
    """Twelve Data API سے OHLCV ڈیٹا حاصل کرتا ہے۔ (اس میں کیشنگ نہیں ہے)"""
    if not TWELVE_DATA_API_KEY:
        raise HTTPException(status_code=500, detail="API key for data provider is not configured.")
    interval_map = {"1m": "1min", "5m": "5min", "15m": "15min"}
    interval = interval_map.get(timeframe)
    if not interval:
        raise ValueError(f"Unsupported timeframe for Twelve Data: {timeframe}")
    url = f"https://api.twelvedata.com/time_series"
    params = {"symbol": symbol, "interval": interval, "outputsize": output_size, "apikey": TWELVE_DATA_API_KEY, "timezone": "UTC"}
    print(f"TWELVE DATA (OHLC): Fetching fresh time series for {symbol} ({interval})...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "ok" or "values" not in data:
            raise ValueError(f"Twelve Data API returned an error: {data.get('message', 'Unknown error')}")
        candles = []
        for item in reversed(data["values"]):
            candles.append({"datetime": item["datetime"], "open": float(item["open"]), "high": float(item["high"]), "low": float(item["low"]), "close": float(item["close"]), "volume": int(item.get("volume", 0))})
        print(f"TWELVE DATA (OHLC): Successfully fetched and processed {len(candles)} candles.")
        return candles
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch data from provider: {e.response.status_code}")
    except Exception as e:
        traceback.print_exc()
        raise

@app.get("/health", status_code=200, tags=["System"])
async def health_check():
    return {"status": "ok", "message": "ScalpMaster AI is running."}

@app.get("/api/price", tags=["Real-time Data"])
async def get_realtime_price(symbol: str = Query("XAU/USD")):
    """تازہ ترین قیمت حاصل کرتا ہے، اور API کالز بچانے کے لیے کیشنگ کا استعمال کرتا ہے۔"""
    now = datetime.utcnow()

    # 1. کیشے چیک کریں
    if symbol in price_cache:
        cached_price, cache_time = price_cache[symbol]
        if now - cache_time < timedelta(seconds=CACHE_DURATION_SECONDS):
            print(f"CACHE HIT: Returning cached price for {symbol}: {cached_price}")
            return {"symbol": symbol, "price": cached_price, "source": "cache"}

    # 2. اگر کیشے پرانی ہے یا موجود نہیں، تو API کال کریں
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
            # 3. نئی قیمت کو کیشے میں محفوظ کریں
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

        print(f"No active signal found. Generating new one using Twelve Data.")
        candles = await fetch_twelve_data_ohlc(symbol, timeframe)
        if not candles or len(candles) < 34:
            raise HTTPException(status_code=404, detail="Not enough historical data for a new signal.")
        
        signal_result = await generate_final_signal(symbol, candles, timeframe)
        
        if signal_result.get("signal") in ["buy", "sell"]:
            add_active_signal(signal_result)
        
        return signal_result
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
        
