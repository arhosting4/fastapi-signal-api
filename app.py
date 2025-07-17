import os
import sys
import traceback
import json
import asyncio
import httpx
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fusion_engine import generate_final_signal
from logger import log_signal
from feedback_checker import check_signals

# --- API کیز کو شروع میں ہی چیک کریں ---
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
MARKETAUX_API_TOKEN = os.getenv("MARKETAUX_API_TOKEN")

if not TWELVE_DATA_API_KEY or not MARKETAUX_API_TOKEN:
    print("FATAL ERROR: Missing required environment variables. Application will not start.")
    sys.exit(1)

print("✅ All required environment variables are present.")

app = FastAPI()

# --- ڈیٹا کیش ---
# یہ متغیر اسکینر سے آنے والے تازہ ترین سگنل ڈیٹا کو محفوظ کرے گا
signal_cache: Dict[str, Any] = {}

# --- کنکشن مینیجر ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- مارکیٹ اسکینر ---
async def market_scanner():
    pairs_to_scan = ["XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY"]
    timeframes_to_scan = ["5min", "15min"]
    await asyncio.sleep(10)

    while True:
        print("🤖 Running Market Scanner...")
        for symbol in pairs_to_scan:
            for timeframe in timeframes_to_scan:
                cache_key = f"{symbol}-{timeframe}"
                try:
                    await asyncio.sleep(8)
                    async with httpx.AsyncClient() as client:
                        candles = await fetch_real_ohlc_data(symbol, timeframe, client)
                    
                    if not candles:
                        print(f"ℹ️ No candle data for {symbol} on {timeframe}, skipping.")
                        continue

                    signal_result = await generate_final_signal(symbol, candles, timeframe)
                    
                    # --- اہم ترین تبدیلی: ڈیٹا کو کیش میں محفوظ کریں ---
                    signal_cache[cache_key] = signal_result
                    
                    if signal_result.get("status") == "ok":
                        print(f"📢 New Signal Found: {symbol} ({timeframe}) - {signal_result.get('signal')}")
                        message = json.dumps({"type": "new_signal", "data": signal_result})
                        await manager.broadcast(message)
                    else: # 'wait' یا 'no-signal' کو بھی براڈکاسٹ کریں تاکہ UI اپ ڈیٹ ہو
                        message = json.dumps({"type": "status_update", "data": signal_result})
                        await manager.broadcast(message)
                        
                except Exception as e:
                    print(f"⚠️ Error scanning {symbol} on {timeframe}: {e}")
        
        print("✅ Market Scanner finished a cycle. Waiting for 1 minute.")
        await asyncio.sleep(60)

# --- بیک گراؤنڈ ٹاسک ---
@app.on_event("startup")
async def startup_event():
    print("✅ Application starting up. Scheduling background tasks.")
    asyncio.create_task(run_feedback_checker_periodically())
    asyncio.create_task(market_scanner())

async def run_feedback_checker_periodically():
    # ... (یہ فنکشن ویسے ہی رہے گا) ...
    while True:
        await asyncio.sleep(300)
        print("🔄 Running Feedback Checker...")
        try:
            closed_signals = await check_signals()
            if closed_signals:
                print(f"📢 Signal Closed: {closed_signals}")
                message = json.dumps({"type": "signal_closed", "data": closed_signals})
                await manager.broadcast(message)
        except Exception as e:
            print(f"Error during scheduled feedback check: {e}")
            traceback.print_exc()

# --- WebSocket اینڈ پوائنٹ ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("🔌 Client disconnected.")

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
    # ... (یہ فنکشن ویسے ہی رہے گا) ...
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={timeframe}&apikey={TWELVE_DATA_API_KEY}&outputsize=100"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = await client.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        if "status" in data and data["status"] == "error":
            print(f"API Error from Twelve Data for {symbol}: {data.get('message', 'Unknown error')}")
            return []
        if "values" not in data or not data["values"]: return []
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
    except Exception as e:
        print(f"Error fetching OHLC data for {symbol}: {e}")
        return []

@app.get("/signal")
async def get_signal(
    symbol: str = Query(..., description="Trading symbol"),
    timeframe: str = Query("5min", description="Timeframe")
):
    # --- اہم ترین تبدیلی: اب یہ اینڈ پوائنٹ کیش سے ڈیٹا واپس کرے گا ---
    cache_key = f"{symbol}-{timeframe}"
    print(f"DEBUG: Manual signal request for {cache_key}")
    
    if cache_key in signal_cache:
        print("✅ Returning data from cache.")
        return signal_cache[cache_key]
    else:
        # اگر کیش میں ڈیٹا نہیں ہے، تو ایک تازہ کال کریں (یہ صرف پہلی بار ہو گا)
        print("⚠️ Cache miss. Fetching live data for manual request...")
        try:
            async with httpx.AsyncClient() as client:
                candles = await fetch_real_ohlc_data(symbol, timeframe, client)
            if not candles:
                raise HTTPException(status_code=404, detail="Could not fetch initial candle data.")
            signal_result = await generate_final_signal(symbol, candles, timeframe)
            signal_cache[cache_key] = signal_result # کیش کو اپ ڈیٹ کریں
            return signal_result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred during live fetch: {str(e)}")
               
