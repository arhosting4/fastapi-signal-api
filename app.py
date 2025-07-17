import os
import sys
import traceback
import json
import asyncio
import httpx
from typing import List

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
    # ان پیئرز اور ٹائم فریمز کو اسکین کریں
    pairs_to_scan = ["XAU/USD", "EUR/USD", "GBP/USD"]
    timeframes_to_scan = ["1min", "5min"]
    
    while True:
        print("🤖 Running Market Scanner...")
        for symbol in pairs_to_scan:
            for timeframe in timeframes_to_scan:
                try:
                    async with httpx.AsyncClient() as client:
                        candles = await fetch_real_ohlc_data(symbol, timeframe, client)
                    
                    signal_result = await generate_final_signal(symbol, candles, timeframe)
                    
                    # صرف نئے "BUY" یا "SELL" سگنلز کو براڈکاسٹ کریں
                    if signal_result.get("status") == "ok":
                        print(f"📢 New Signal Found: {symbol} ({timeframe}) - {signal_result.get('signal')}")
                        # پیغام کو JSON سٹرنگ میں تبدیل کریں
                        message = json.dumps({
                            "type": "new_signal",
                            "data": signal_result
                        })
                        await manager.broadcast(message)
                        
                except Exception as e:
                    print(f"⚠️ Error scanning {symbol} on {timeframe}: {e}")
                
                await asyncio.sleep(5) # ہر API کال کے درمیان تھوڑا وقفہ
        
        print("✅ Market Scanner finished a cycle. Waiting for next run...")
        await asyncio.sleep(60) # ہر مکمل اسکین کے بعد 1 منٹ انتظار کریں

# --- بیک گراؤنڈ ٹاسک ---
@app.on_event("startup")
async def startup_event():
    print("✅ Application starting up. Scheduling background tasks.")
    asyncio.create_task(run_feedback_checker_periodically())
    asyncio.create_task(market_scanner()) # مارکیٹ اسکینر کو شروع کریں

async def run_feedback_checker_periodically():
    while True:
        await asyncio.sleep(300) # 5 منٹ انتظار کریں
        print("🔄 Running Feedback Checker...")
        try:
            closed_signals = await check_signals()
            if closed_signals:
                print(f"📢 Signal Closed: {closed_signals}")
                message = json.dumps({
                    "type": "signal_closed",
                    "data": closed_signals
                })
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
            # فرنٹ اینڈ سے آنے والے پیغامات کو سنیں (اگر ضرورت ہو)
            data = await websocket.receive_text()
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
            raise HTTPException(status_code=500, detail=f"Twelve Data API Error: {data.get('message', 'Unknown error')}")
        if "values" not in data or not data["values"]:
            return [] # خالی لسٹ واپس کریں تاکہ کریش نہ ہو
        ohlc_data = []
        for entry in reversed(data["values"]):
            try:
                ohlc_data.append({
                    "datetime": entry["datetime"], "open": float(entry["open"]),
                    "high": float(entry["high"]), "low": float(entry["low"]),
                    "close": float(entry["close"]), "volume": float(entry.get("volume", 0))
                })
            except (ValueError, KeyError):
                continue
        return ohlc_data
    except Exception as e:
        print(f"Error fetching OHLC data for {symbol}: {e}")
        return [] # ایرر کی صورت میں بھی خالی لسٹ واپس کریں

@app.get("/signal")
async def get_signal(
    symbol: str = Query(..., description="Trading symbol"),
    timeframe: str = Query("5min", description="Timeframe")
):
    # یہ اینڈ پوائنٹ اب صرف دستی (manual) سگنل حاصل کرنے کے لیے ہے
    print(f"DEBUG: Manual signal request for {symbol} on {timeframe}")
    try:
        async with httpx.AsyncClient() as client:
            candles = await fetch_real_ohlc_data(symbol, timeframe, client)
        
        if not candles:
            raise HTTPException(status_code=404, detail="Could not fetch candle data.")
            
        signal_result = await generate_final_signal(symbol, candles, timeframe)
        log_signal(symbol, signal_result, candles)
        return signal_result
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"CRITICAL ERROR in get_signal for {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")
