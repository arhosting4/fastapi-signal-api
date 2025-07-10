from fastapi import FastAPI, HTTPException, Query
from fusion_engine import generate_final_signal
from logger import log_signal
from feedback_checker import check_signals
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
import httpx
import traceback
import json

app = FastAPI()

# Initialize the scheduler
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

# Environment Variables
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
        print("✅ Telegram response:", response.status_code, response.text)
    except httpx.RequestError as e:
        print(f"⚠️ Telegram Send Failed: {e}")
    except Exception as e:
        print(f"⚠️ An unexpected error occurred during Telegram send: {e}")

async def fetch_real_ohlc_data(symbol: str, interval: str) -> list:
    if not TWELVE_DATA_API_KEY:
        raise ValueError("TWELVE_DATA_API_KEY is not set in environment variables.")
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={TWELVE_DATA_API_KEY}&outputsize=100"
    print(f"DEBUG: Trying Twelve Data API URL: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        async with httpx.AsyncClient() as client:
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
                    "datetime": entry["datetime"], "open": float(entry["open"]), "high": float(entry["high"]),
                    "low": float(entry["low"]), "close": float(entry["close"]), "volume": float(entry.get("volume", 0))
                })
            except ValueError as ve:
                print(f"⚠️ Data conversion error for {symbol} entry {entry}: {ve}")
                continue
        if not ohlc_data:
            raise HTTPException(status_code=404, detail=f"No valid OHLC data could be parsed for {symbol}.")
        return ohlc_data
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Twelve Data API request timed out for {symbol}.")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Network or API connection error: {e}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Error parsing Twelve Data response: {e}")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {e}")

@app.get("/")
def root():
    return {"message": "ScalpMasterAi API is running. Visit /docs for API documentation."}

@app.get("/signal")
async def get_signal(symbol: str = Query(..., description="Trading symbol (e.g., AAPL, EUR/USD)"), timeframe: str = Query("1min", description="Candle interval")):
    print(f"DEBUG: Received symbol: {symbol}, timeframe: {timeframe}")
    try:
        candles = await fetch_real_ohlc_data(symbol, timeframe)
        signal_result = generate_final_signal(symbol, candles, timeframe)
        log_signal(symbol, signal_result, candles)
        
        signal_type = signal_result.get('signal', 'N/A').upper()
        if signal_result.get("status") == "ok" and signal_type in ["BUY", "SELL"]:
            tp = signal_result.get('tp')
            sl = signal_result.get('sl')
            tp_sl_info = ""
            if tp is not None and sl is not None:
                tp_sl_info = f"\n\n🎯 TP: *{tp:.5f}* | 🛑 SL: *{sl:.5f}*"
            message = (
                f"📈 ScalpMaster AI Signal Alert 📈\n\n"
                f"Symbol: *{signal_result.get('symbol', symbol).upper()}*\n"
                f"Timeframe: *{signal_result.get('timeframe', timeframe)}*\n"
                f"Signal: *{signal_type}*\n"
                f"Price: *{signal_result.get('price'):.5f}*\n"
                f"Confidence: *{signal_result.get('confidence', 0.0):.2f}%*\n"
                f"Tier: *{signal_result.get('tier', 'N/A')}*\n"
                f"Pattern: *{signal_result.get('pattern', 'N/A')}*\n"
                f"Reason: _{signal_result.get('reason', 'N/A')}_"
                f"{tp_sl_info}\n\n"
                f"Risk: {signal_result.get('risk', 'N/A')} | News: {signal_result.get('news', 'N/A')}"
            )
            send_telegram_message(message)
        
        return signal_result
    except HTTPException as e:
        raise e
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {e}")
                
