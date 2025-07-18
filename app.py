import os
import traceback
import asyncio
import httpx # yfinance کی جگہ API کالز کے لیے
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pandas as pd # pandas اب بھی ڈیٹا کی ترتیب کے لیے استعمال ہوگا

# ہمارے اپنے ماڈیولز
from feedback_checker import check_active_signals_job
from fusion_engine import generate_final_signal
from signal_tracker import get_active_signal_for_timeframe, add_active_signal

# --- Twelve Data API کلید کو ماحول سے لوڈ کریں ---
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

app = FastAPI(title="ScalpMaster AI API")

# --- شیڈیولر کی شروعات ---
scheduler = AsyncIOScheduler(timezone="UTC")

@app.on_event("startup")
async def startup_event():
    if not TWELVE_DATA_API_KEY:
        print("CRITICAL WARNING: TWELVE_DATA_API_KEY is not set. The application will not work correctly.")
    scheduler.add_job(check_active_signals_job, 'interval', seconds=60, id="signal_check_job")
    scheduler.start()
    print("APScheduler started. Signal checker is running every 60 seconds.")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    print("APScheduler has been shut down.")

# --- اہم تبدیلی: yfinance کی جگہ نیا فنکشن ---
async def fetch_twelve_data_ohlc(symbol: str, timeframe: str, output_size: int = 100):
    """Twelve Data API سے OHLCV ڈیٹا حاصل کرتا ہے۔"""
    if not TWELVE_DATA_API_KEY:
        raise HTTPException(status_code=500, detail="API key for data provider is not configured.")

    # Twelve Data کے لیے ٹائم فریم فارمیٹ
    interval_map = {"1m": "1min", "5m": "5min", "15m": "15min"}
    interval = interval_map.get(timeframe)
    if not interval:
        raise ValueError(f"Unsupported timeframe for Twelve Data: {timeframe}")

    url = f"https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": output_size,
        "apikey": TWELVE_DATA_API_KEY,
        "timezone": "UTC"
    }
    
    print(f"TWELVE DATA: Fetching time series for {symbol} ({interval})...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=20)
        response.raise_for_status() # اگر 4xx یا 5xx ہو تو ایرر دے
        data = response.json()

        if data.get("status") != "ok" or "values" not in data:
            raise ValueError(f"Twelve Data API returned an error: {data.get('message', 'Unknown error')}")

        # ڈیٹا کو صحیح فارمیٹ میں تبدیل کریں (پرانے فارمیٹ کی طرح)
        candles = []
        for item in reversed(data["values"]): # API نیا ڈیٹا پہلے دیتی ہے، ہمیں پرانا پہلے چاہیے
            candles.append({
                "datetime": item["datetime"],
                "open": float(item["open"]),
                "high": float(item["high"]),
                "low": float(item["low"]),
                "close": float(item["close"]),
                "volume": int(item.get("volume", 0)) # حجم ہمیشہ موجود نہیں ہوتا
            })
        
        print(f"TWELVE DATA: Successfully fetched and processed {len(candles)} candles.")
        return candles
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error fetching from Twelve Data: {e.response.text}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch data from provider: {e.response.status_code}")
    except Exception as e:
        print(f"CRITICAL: Error processing data from Twelve Data: {e}")
        traceback.print_exc()
        raise

# (باقی API اینڈ پوائنٹس اب نئے فنکشن کا استعمال کریں گے)
@app.get("/health", status_code=200, tags=["System"])
async def health_check():
    return {"status": "ok", "message": "ScalpMaster AI is running."}

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
        print(f"CRITICAL SERVER ERROR in get_signal for {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
            
