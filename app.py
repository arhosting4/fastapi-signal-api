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
if not TWELVE_DATA_API_KEY:
    print("--- CRITICAL: TWELVE_DATA_API_KEY environment variable is not set. ---")
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
    print(f"➡️ [FETCH] Attempting to fetch data for {symbol} ({timeframe})...")
    
    # *** حتمی اور فول پروف حل: API کی کو براہ راست URL میں شامل کریں ***
    # ہم تمام پراکسی اور ہیڈرز کو ہٹا رہے ہیں اور سب سے سادہ طریقہ استعمال کر رہے ہیں
    base_url = "https://api.twelvedata.com/time_series"
    
    # پیرامیٹرز کو ایک ڈکشنری میں بنائیں
    params = {
        "symbol": symbol,
        "interval": timeframe,
        "apikey": TWELVE_DATA_API_KEY, # API کی کو یہاں شامل کریں
        "outputsize": 100
    }
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    print(f"DEBUG: Making a direct call to Twelve Data with params.")

    try:
        # httpx کو پیرامیٹرز کی ڈکشنری دیں، وہ خود ہی اسے صحیح طریقے سے URL میں شامل کر دے گا
        response = await client.get(base_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "status" in data and data["status"] == "error":
            # یہ وہی ایرر ہے جو ہمیں مل رہا تھا
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
    except httpx.HTTPStatusError as e:
        print(f"❌ [FETCH] HTTP Status Error (likely IP block or server issue): {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail="Could not connect to the data provider.")
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
        print(f"❌ [SIGNAL] HTTP Exception occurred: {e.detail}")
        raise e
    except Exception as e:
        print(f"❌ [SIGNAL] CRITICAL ERROR in get_signal for {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")
    
