from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fusion_engine import generate_final_signal
from logger import log_signal
from feedback_checker import check_signals
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
import httpx
import traceback
import json

app = FastAPI()

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    scheduler.add_job(check_signals, 'interval', minutes=15)
    scheduler.start()
    print("APScheduler started. Feedback checker is scheduled to run every 15 minutes.")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    print("APScheduler shut down.")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

def send_telegram_message(message: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram credentials not set. Skipping message send.")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        response = httpx.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})
        response.raise_for_status()
    except Exception as e:
        print(f"⚠️ Telegram Send Failed: {e}")

async def fetch_real_ohlc_data(symbol: str, interval: str) -> list:
    if not TWELVE_DATA_API_KEY:
        raise ValueError("TWELVE_DATA_API_KEY is not set.")
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={TWELVE_DATA_API_KEY}&outputsize=100"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
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
                    "datetime": entry["datetime"], "open": float(entry["open"]), "high": float(entry["high"]),
                    "low": float(entry["low"]), "close": float(entry["close"]), "volume": float(entry.get("volume", 0))
                })
            except ValueError: continue
        return ohlc_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {e}")

@app.get("/")
async def read_index():
    return FileResponse('frontend/index.html')

@app.get("/signal")
async def get_signal(symbol: str = Query(..., description="Trading symbol"), timeframe: str = Query("1min", description="Candle interval")):
    try:
        candles = await fetch_real_ohlc_data(symbol, timeframe)
        signal_result = generate_final_signal(symbol, candles, timeframe)
        log_signal(symbol, signal_result, candles)

        # *** اہم تبدیلی: کینڈل ڈیٹا کو رسپانس میں شامل کریں ***
        signal_result["candles"] = candles 

        # ... (ٹیلی گرام بھیجنے والا کوڈ وہی رہے گا) ...
        
        return signal_result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {e}")
        
