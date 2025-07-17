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
    pairs_to_scan = ["XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY"]
    timeframes_to_scan = ["5min", "15min"] # چھوٹے ٹائم فریمز کو کم کریں
    
    await asyncio.sleep(15) # ایپلیکیشن کے شروع ہونے کے 15 سیکنڈ بعد اسکینر شروع کریں

    while True:
        print("🤖 Running Market Scanner...")
        for symbol in pairs_to_scan:
            for timeframe in timeframes_to_scan:
                try:
                    # ہر API کال کے درمیان وقفہ بڑھائیں تاکہ ریٹ لمٹ سے بچا جا سکے
                    # 8 کالز فی منٹ سے کم رہنے کے لیے (8 * 8 = 64 سیکنڈ)
                    await asyncio.sleep(8) 

                    async with httpx.AsyncClient() as client:
                        candles = await fetch_real_ohlc_data(symbol, timeframe, client)
                    
                    if not candles:
                        print(f"ℹ️ No candle data for {symbol} on {timeframe}, skipping.")
                        continue # اگر ڈیٹا نہ ملے تو اگلی آئٹم پر جائیں

                    signal_result = await generate_final_signal(symbol, candles, timeframe)
                    
                    if signal_result.get("status") == "ok":
                        print(f"📢 New Signal Found: {symbol} ({timeframe}) - {signal_result.get('signal')}")
                        message = json.dumps({
                            "type": "new_signal",
                            "data": signal_result
                        })
                        await manager.broadcast(message)
                        
                except Exception as e:
                    print(f"⚠️ Error scanning {symbol} on {timeframe}: {e}")
        
        print("✅ Market Scanner finished a cycle. Waiting for 1 minute before next cycle.")
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
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={timeframe}&apikey={TWELVE_DATA_API_KEY}&outputsize=100"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = await client.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        if "status" in data and data["status"] == "error":
            # اس ایرر کو لاگ کریں لیکن کریش نہ ہوں
            print(f"API Error from Twelve Data for {symbol}: {data.get('message', 'Unknown error')}")
            return []
        if "values" not in data or not data["values"]:
            return []
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
        return []

@app.get("/signal")
async def get_signal(
    symbol: str = Query(..., description="Trading symbol"),
    timeframe: str = Query("5min", description="Timeframe")
):
    print(f"DEBUG: Manual signal request for {symbol} on {timeframe}")
    try:
        async with httpx.AsyncClient() as client:
            candles = await fetch_real_ohlc_data(symbol, timeframe, client)
        
        if not candles:
            raise HTTPException(status_code=404, detail="Could not fetch candle data. The API limit may have been reached or the symbol is invalid.")
            
        signal_result = await generate_final_signal(symbol, candles, timeframe)
        log_signal(symbol, signal_result, candles)
        return signal_result
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"CRITICAL ERROR in get_signal for {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")
    
