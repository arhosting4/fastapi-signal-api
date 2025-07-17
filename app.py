import os
import sys
import traceback
import json
import asyncio
import httpx
import time # Finnhub کے لیے ٹائم اسٹیمپ بنانے کے لیے
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fusion_engine import generate_final_signal
from logger import log_signal
from feedback_checker import check_signals

# --- نئی API کی کو چیک کریں ---
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
if not FINNHUB_API_KEY:
    print("--- CRITICAL: FINNHUB_API_KEY environment variable is not set. ---")
    sys.exit(1)

app = FastAPI()

# --- بیک گراؤنڈ ٹاسک (کوئی تبدیلی نہیں) ---
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

# --- ہیلتھ چیک (کوئی تبدیلی نہیں) ---
@app.get("/health", status_code=200)
async def health_check():
    print("ጤ [HEALTH] Health check endpoint was called.")
    return {"status": "ok"}

# --- فرنٹ اینڈ اور سگنل اینڈ پوائنٹس ---
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/")
async def read_root():
    return FileResponse('frontend/index.html')

# *** اہم ترین تبدیلی: Finnhub سے ڈیٹا حاصل کرنے کا نیا فنکشن ***
async def fetch_real_ohlc_data(symbol: str, timeframe: str, client: httpx.AsyncClient) -> list:
    print(f"➡️ [FETCH] Attempting to fetch data for {symbol} ({timeframe}) from Finnhub...")
    
    # Finnhub کے لیے سمبل اور ٹائم فریم کو فارمیٹ کریں
    finnhub_symbol = f"OANDA:{symbol.replace('/', '_')}" # XAU/USD -> OANDA:XAU_USD
    
    # Finnhub کے لیے ٹائم فریم میپنگ
    resolution_map = {
        "1min": "1", "5min": "5", "15min": "15"
    }
    if timeframe not in resolution_map:
        raise HTTPException(status_code=400, detail="Unsupported timeframe for Finnhub.")
    resolution = resolution_map[timeframe]

    # Finnhub کو 'from' اور 'to' ٹائم اسٹیمپ کی ضرورت ہوتی ہے
    end_time = int(time.time())
    # ہم تقریباً 200 کینڈلز کا ڈیٹا حاصل کرنے کی کوشش کریں گے
    # 15 منٹ کے لیے: 200 * 15 * 60 = 3 دن پہلے
    start_time = end_time - (200 * int(resolution) * 60 * 3) 

    # Finnhub API کا URL
    params = {
        "symbol": finnhub_symbol,
        "resolution": resolution,
        "from": start_time,
        "to": end_time,
        "token": FINNHUB_API_KEY
    }
    base_url = "https://finnhub.io/api/v1/forex/candle"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = await client.get(base_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("s") != "ok":
            print(f"❌ [FETCH] Finnhub returned an error or no data: {data}")
            raise HTTPException(status_code=404, detail="No data received from Finnhub. Check symbol or timeframe.")
        
        print(f"✅ [FETCH] Successfully fetched {len(data.get('c', []))} candles for {symbol}.")
        
        # Finnhub کا ڈیٹا فارمیٹ مختلف ہے، اسے اپنے فارمیٹ میں تبدیل کریں
        ohlc_data = []
        # Finnhub تمام قیمتوں کو الگ الگ فہرستوں میں بھیجتا ہے
        for i in range(len(data['c'])):
            ohlc_data.append({
                "datetime": time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(data['t'][i])),
                "open": float(data['o'][i]),
                "high": float(data['h'][i]),
                "low": float(data['l'][i]),
                "close": float(data['c'][i]),
                "volume": float(data.get('v', [0]*len(data['c']))[i]) # حجم (volume)
            })
        return ohlc_data
    except httpx.HTTPStatusError as e:
        print(f"❌ [FETCH] HTTP Status Error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail="Could not connect to the data provider.")
    except Exception as e:
        print(f"❌ [FETCH] An unexpected error occurred: {e}")
        traceback.print_exc()
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
        
