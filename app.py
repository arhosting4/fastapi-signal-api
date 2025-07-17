import os
import sys
import traceback
import json
import asyncio
import httpx
import time
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fusion_engine import generate_final_signal
from logger import log_signal
from feedback_checker import check_signals

# --- API کی کو چیک کریں ---
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
if not FINNHUB_API_KEY:
    print("--- CRITICAL: FINNHUB_API_KEY environment variable is not set. ---")
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

# *** اہم ترین تبدیلی: Finnhub سے ڈیٹا حاصل کرنے کا نیا اور ڈیبگنگ کے لیے تیار فنکشن ***
async def fetch_real_ohlc_data(symbol: str, timeframe: str, client: httpx.AsyncClient) -> list:
    print(f"➡️ [FETCH] Attempting to fetch data for {symbol} ({timeframe}) from Finnhub...")
    
    finnhub_symbol = f"OANDA:{symbol.replace('/', '_')}"
    print(f"DEBUG: Converted symbol to Finnhub format: {finnhub_symbol}")
    
    resolution_map = {"1min": "1", "5min": "5", "15min": "15"}
    if timeframe not in resolution_map:
        raise HTTPException(status_code=400, detail="Unsupported timeframe for Finnhub.")
    resolution = resolution_map[timeframe]

    end_time = int(time.time())
    start_time = end_time - (200 * int(resolution) * 60 * 3) 

    params = {
        "symbol": finnhub_symbol, "resolution": resolution,
        "from": start_time, "to": end_time, "token": FINNHUB_API_KEY
    }
    base_url = "https://finnhub.io/api/v1/forex/candle"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = await client.get(base_url, params=params, headers=headers, timeout=30)
        
        # *** اہم ترین ڈیبگنگ کا مرحلہ: جواب کو چیک کریں ***
        try:
            data = response.json()
        except json.JSONDecodeError:
            # اگر جواب JSON نہیں ہے (مثلاً، HTML ایرر پیج)
            print(f"❌ [FETCH] Finnhub did not return valid JSON. Status: {response.status_code}")
            print(f"Raw Response: {response.text}")
            raise HTTPException(status_code=502, detail=f"Invalid response from data provider: {response.text[:200]}")

        # اگر جواب JSON ہے، تو اسے چیک کریں
        if response.status_code != 200 or data.get("s") != "ok":
            print(f"❌ [FETCH] Finnhub returned an error. Status: {response.status_code}, Data: {data}")
            # **ایرر کو براہ راست فرنٹ اینڈ پر بھیجیں**
            error_message = data.get('error', f"Unknown error from Finnhub. Status: {response.status_code}")
            raise HTTPException(status_code=502, detail=f"Finnhub API Error: {error_message}")

        print(f"✅ [FETCH] Successfully fetched {len(data.get('c', []))} candles for {symbol}.")
        
        ohlc_data = []
        for i in range(len(data['c'])):
            ohlc_data.append({
                "datetime": time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(data['t'][i])),
                "open": float(data['o'][i]), "high": float(data['h'][i]),
                "low": float(data['l'][i]), "close": float(data['c'][i]),
                "volume": float(data.get('v', [0]*len(data['c']))[i])
            })
        return ohlc_data

    except httpx.TimeoutException:
        print("❌ [FETCH] Request to Finnhub timed out.")
        raise HTTPException(status_code=504, detail="Connection to data provider timed out.")
    except httpx.RequestError as e:
        print(f"❌ [FETCH] A network request error occurred: {e}")
        raise HTTPException(status_code=503, detail=f"Could not connect to the data provider. Network issue.")
    except Exception as e:
        print(f"❌ [FETCH] An unexpected error occurred in fetch_real_ohlc_data: {e}")
        traceback.print_exc()
        # اگر یہ HTTPException ہے، تو اسے دوبارہ بھیجیں، ورنہ ایک نیا بنائیں
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")


@app.get("/signal")
async def get_signal(
    symbol: str = Query("XAU/USD", description="Trading symbol"),
    timeframe: str = Query("5min", description="Timeframe")
):
    print(f"🚀 [SIGNAL] Received request for {symbol} on {timeframe}.")
    try:
        async with httpx.AsyncClient() as client:
            candles = await fetch_real_ohlc_data(symbol, timeframe, client)
        
        if not candles:
             raise HTTPException(status_code=404, detail="Could not fetch any candle data.")

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
                                                                           
