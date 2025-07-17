import os
import sys
import traceback
import json
import asyncio
import httpx
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fusion_engine import generate_final_signal
from logger import log_signal
from feedback_checker import check_signals

# --- API کیز کو شروع میں ہی چیک کریں ---
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
MARKETAUX_API_TOKEN = os.getenv("MARKETAUX_API_TOKEN")

if not TWELVE_DATA_API_KEY or not MARKETAUX_API_TOKEN:
    print("FATAL ERROR: Missing required environment variables.")
    sys.exit(1)

app = FastAPI()

# --- بیک گراؤنڈ ٹاسک (صرف فیڈ بیک چیکر) ---
@app.on_event("startup")
async def startup_event():
    print("✅ Application starting up. Scheduling feedback checker.")
    asyncio.create_task(run_feedback_checker_periodically())

async def run_feedback_checker_periodically():
    while True:
        await asyncio.sleep(300) # 5 منٹ انتظار کریں
        print("🔄 Running Feedback Checker...")
        try:
            await check_signals()
        except Exception as e:
            print(f"Error during scheduled feedback check: {e}")

# --- ہیلتھ چیک اینڈ پوائنٹ ---
@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

# --- فرنٹ اینڈ اور سگنل اینڈ پوائنٹس ---
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/")
async def read_root():
    return FileResponse('frontend/index.html')

async def fetch_real_ohlc_data(symbol: str, timeframe: str, client: httpx.AsyncClient) -> list:
    # *** اہم ترین تبدیلی: پراکسی کا استعمال ***
    # ہم اپنی API کال کو ایک پراکسی کے ذریعے بھیجیں گے تاکہ IP بلاکنگ سے بچا جا سکے
    proxy_url = "https://cors-anywhere.herokuapp.com/"
    target_url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={timeframe}&apikey={TWELVE_DATA_API_KEY}&outputsize=100"
    
    # پراکسی کے لیے ایک خاص ہیڈر کی ضرورت ہوتی ہے
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'X-Requested-With': 'XMLHttpRequest' # یہ ہیڈر CORS Anywhere کے لیے ضروری ہے
    }
    
    print(f"DEBUG: Fetching via proxy: {proxy_url}{target_url}")

    try:
        response = await client.get(f"{proxy_url}{target_url}", headers=headers, timeout=30) # ٹائم آؤٹ کو بڑھا دیا گیا ہے
        response.raise_for_status()
        data = response.json()
        
        if "status" in data and data["status"] == "error":
            raise HTTPException(status_code=400, detail=f"API Error: {data.get('message', 'Unknown error')}")
        if "values" not in data or not data["values"]:
            raise HTTPException(status_code=404, detail="No data found for this symbol/timeframe.")
        
        ohlc_data = []
        for entry in reversed(data["values"]):
            try:
                ohlc_data.append({
                    "datetime": entry["datetime"], "open": float(entry["open"]),
                    "high": float(entry["high"]), "low": float(entry["low"]),
                    "close": float(entry["close"]), "volume": float(entry.get("volume", 0))
                })
            except (ValueError, KeyError): continue
        return ohlc_data
    except httpx.ReadTimeout:
        raise HTTPException(status_code=504, detail="API request via proxy timed out. Please try again.")
    except Exception as e:
        print(f"Error fetching OHLC data via proxy for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch data from the provider via proxy.")

@app.get("/signal")
async def get_signal(
    symbol: str = Query("XAU/USD", description="Trading symbol"),
    timeframe: str = Query("5min", description="Timeframe")
):
    print(f"DEBUG: Signal request for {symbol} on {timeframe}")
    try:
        async with httpx.AsyncClient() as client:
            candles = await fetch_real_ohlc_data(symbol, timeframe, client)
        
        signal_result = await generate_final_signal(symbol, candles, timeframe)
        log_signal(symbol, signal_result, candles)
        return signal_result
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"CRITICAL ERROR in get_signal for {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")
                        
