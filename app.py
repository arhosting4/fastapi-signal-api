import os
import sys
import traceback
import json
import asyncio
import httpx
from typing import List, Dict, Any
from urllib.parse import urlencode

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
    print("--- CRITICAL: Missing required environment variables. ---")
    sys.exit(1)

app = FastAPI()

# --- بیک گراؤنڈ ٹاسک ---
@app.on_event("startup")
async def startup_event():
    print("✅ [STARTUP] Application is starting. Scheduling feedback checker.")
    asyncio.create_task(run_feedback_checker_periodically())

async def run_feedback_checker_periodically():
    while True:
        await asyncio.sleep(300)
        print("🔄 [BACKGROUND] Running Feedback Checker...")
        try:
            await check_signals()
            print("✅ [BACKGROUND] Feedback check completed successfully.")
        except Exception as e:
            print(f"❌ [BACKGROUND] Error during feedback check: {e}")

# --- ہیلتھ چیک ---
@app.get("/health", status_code=200)
async def health_check():
    print("ጤ [HEALTH] Health check endpoint was called.")
    return {"status": "ok"}

# --- فرنٹ اینڈ اور سگنل اینڈ پوائنٹس ---
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/")
async def read_root():
    return FileResponse('frontend/index.html')

async def fetch_real_ohlc_data(symbol: str, timeframe: str, client: httpx.AsyncClient) -> list:
    print(f"➡️ [FETCH] Attempting to fetch data for {symbol} ({timeframe}) via proxy...")
    base_url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol, "interval": timeframe,
        "apikey": TWELVE_DATA_API_KEY, "outputsize": 100
    }
    target_url = f"{base_url}?{urlencode(params)}"
    proxy_url = f"https://api.allorigins.win/get?url={target_url}"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = await client.get(proxy_url, headers=headers, timeout=40)
        response.raise_for_status()
        proxy_data = response.json()
        
        if 'contents' not in proxy_data or proxy_data['contents'] is None:
            print(f"❌ [FETCH] Proxy returned empty or null contents for {symbol}.")
            raise HTTPException(status_code=502, detail="Proxy returned empty contents.")
            
        data = json.loads(proxy_data['contents'])

        if "status" in data and data["status"] == "error":
            print(f"❌ [FETCH] API provider returned an error: {data.get('message')}")
            raise HTTPException(status_code=400, detail=f"API Error: {data.get('message', 'Unknown error')}")
        if "values" not in data or not data["values"]:
            print(f"❌ [FETCH] No 'values' in data for {symbol}.")
            raise HTTPException(status_code=404, detail="No data found for this symbol/timeframe.")
        
        print(f"✅ [FETCH] Successfully fetched {len(data['values'])} candles for {symbol}.")
        
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
        print(f"❌ [FETCH] Request timed out for {symbol}.")
        raise HTTPException(status_code=504, detail="API request via proxy timed out.")
    except Exception as e:
        print(f"❌ [FETCH] An unexpected error occurred: {e}")
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Could not process data: {str(e)}")

@app.get("/signal")
async def get_signal(
    symbol: str = Query("XAU/USD", description="Trading symbol"),
    timeframe: str = Query("5min", description="Timeframe")
):
    print(f"🚀 [SIGNAL] Received request for {symbol} on {timeframe}.")
    try:
        async with httpx.AsyncClient() as client:
            candles = await fetch_real_ohlc_data(symbol, timeframe, client)
        
        print(f"🧠 [AI] Generating signal for {symbol}...")
        signal_result = await generate_final_signal(symbol, candles, timeframe)
        print(f"📄 [AI] Signal generated: {signal_result.get('signal')}")
        
        print(f"💾 [LOG] Logging signal for {symbol}...")
        log_signal(symbol, signal_result, candles)
        
        print(f"✅ [SIGNAL] Successfully processed request for {symbol}.")
        return signal_result
    except HTTPException as e:
        # HTTPException کو براہ راست بھیجیں
        print(f"❌ [SIGNAL] HTTP Exception occurred: {e.detail}")
        raise e
    except Exception as e:
        print(f"❌ [SIGNAL] CRITICAL ERROR in get_signal for {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")
        
