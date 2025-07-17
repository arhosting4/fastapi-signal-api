from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler # <-- اسے تبدیل کریں
from feedback_checker import check_signals
import httpx
import traceback
import json
import os
from fusion_engine import generate_final_signal
from logger import log_signal
import asyncio # <-- asyncio کو امپورٹ کریں

app = FastAPI()

# Twelve Data API Key
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
MARKETAUX_API_TOKEN = os.getenv("MARKETAUX_API_TOKEN")

async def fetch_real_ohlc_data(symbol: str, timeframe: str, client: httpx.AsyncClient) -> list:
    # ... (یہ فنکشن ویسے ہی رہے گا، کوئی تبدیلی نہیں) ...
    if not TWELVE_DATA_API_KEY:
        raise ValueError("TWELVE_DATA_API_KEY is not set in environment variables.")
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={timeframe}&apikey={TWELVE_DATA_API_KEY}&outputsize=100"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = await client.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "status" in data and data["status"] == "error":
            raise HTTPException(status_code=500, detail=f"Twelve Data API Error: {data.get('message', 'Unknown error')}")
        if "values" not in data or not data["values"]:
            raise HTTPException(status_code=404, detail=f"No OHLC data found for {symbol}.")
        ohlc_data = []
        for entry in reversed(data["values"]):
            try:
                ohlc_data.append({
                    "datetime": entry["datetime"], "open": float(entry["open"]),
                    "high": float(entry["high"]), "low": float(entry["low"]),
                    "close": float(entry["close"]), "volume": float(entry.get("volume", 0))
                })
            except (ValueError, KeyError) as ve:
                print(f"⚠️ Data conversion error for {symbol} entry {entry}: {ve}")
                continue
        if not ohlc_data:
            raise HTTPException(status_code=404, detail=f"No valid OHLC data could be parsed for {symbol}.")
        return ohlc_data
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Twelve Data API request timed out.")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Network or API connection error: {e}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error parsing Twelve Data response.")

# --- اہم تبدیلی: شیڈولر کو async بنائیں ---
@app.on_event("startup")
async def startup_event():
    """
    ایپلیکیشن کے شروع ہونے پر شیڈولر کو چلائیں
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_signals, 'interval', minutes=15)
    scheduler.start()
    print("✅ Async Background scheduler started.")
    # اس بات کو یقینی بنائیں کہ شیڈولر پس منظر میں چلتا رہے
    asyncio.create_task(scheduler._main_loop())


# فرنٹ اینڈ فائلوں کو پیش کریں
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/")
async def read_root():
    return FileResponse('frontend/index.html')

@app.get("/signal")
async def get_signal(
    symbol: str = Query(..., description="Trading symbol (e.g., AAPL, EUR/USD)"),
    timeframe: str = Query("5min", description="Timeframe (e.g., 1min, 5min, 1h)")
):
    # ... (یہ فنکشن ویسے ہی رہے گا، کوئی تبدیلی نہیں) ...
    print(f"DEBUG: Received symbol: {symbol}, Timeframe: {timeframe}")
    try:
        async with httpx.AsyncClient() as client:
            candles = await fetch_real_ohlc_data(symbol, timeframe, client)
        signal_result = await generate_final_signal(symbol, candles, timeframe)
        log_signal(symbol, signal_result, candles)
        return signal_result
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"CRITICAL ERROR in app.py for {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")
        
