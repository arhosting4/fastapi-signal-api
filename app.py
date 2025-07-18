import os
import traceback
import asyncio
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import yfinance as yf
import pandas as pd

# --- AI اور ہیلپر ماڈیولز کو امپورٹ کریں ---
# (یہ فرض کیا جا رہا ہے کہ یہ فائلیں موجود ہیں)
# from fusion_engine import generate_final_signal
# from logger import log_signal
# from feedback_checker import check_signals
# from signal_tracker import add_active_signal

# --- فرضی فنکشنز (اگر اصل فائلیں موجود نہیں ہیں) ---
async def generate_final_signal(symbol, candles, timeframe):
    if not candles or len(candles) < 2:
        return {"signal": "wait", "reason": "Not enough data."}
    return {
        "signal": "buy" if candles[-1]['close'] > candles[-2]['close'] else "sell",
        "confidence": 75.5, "tier": "Tier 2", "reason": "A test reason.",
        "tp": candles[-1]['close'] * 1.01, "sl": candles[-1]['close'] * 0.99
    }
def log_signal(symbol, result, candles): pass
async def check_signals(): print("Checking signals...")
def add_active_signal(result): pass
# --- ختم: فرضی فنکشنز ---


# --- FastAPI ایپ کی شروعات ---
app = FastAPI()

# --- اہم: سیکیورٹی ہیڈرز (CSP) کے لیے مڈل ویئر ---
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' https://scalpmasterai.in data:; "
        "connect-src 'self' https://*.yfinance.com;"  # yfinance کے لیے شامل کیا گیا
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

# --- ہیلپر فنکشنز ---
def get_yfinance_symbol(symbol: str) -> str:
    if symbol.upper() == "XAU/USD": return "GC=F"
    return symbol

async def fetch_real_ohlc_data(symbol: str, timeframe: str):
    yfinance_symbol = get_yfinance_symbol(symbol)
    period_map = {"1m":"2d", "5m":"5d", "15m":"10d", "1h":"1mo", "4h":"3mo", "1d":"1y"}
    period = period_map.get(timeframe, "5d")
    print(f"YAHOO FINANCE: Fetching data for '{yfinance_symbol}' ({timeframe}, {period})...")
    try:
        data = await asyncio.to_thread(
            yf.download, tickers=yfinance_symbol, period=period, interval=timeframe,
            progress=False, auto_adjust=False
        )
        if data.empty: raise ValueError(f"No data returned for '{yfinance_symbol}'.")
        data.reset_index(inplace=True)
        data.columns = [str(col).lower() for col in data.columns]
        rename_dict = {'date': 'datetime', 'index': 'datetime'}
        data.rename(columns={k: v for k, v in rename_dict.items() if k in data.columns}, inplace=True)
        required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"Missing required column '{col}'. Available: {data.columns.to_list()}")
        data['datetime'] = pd.to_datetime(data['datetime'], utc=True).dt.strftime('%Y-%m-%d %H:%M:%S')
        candles = data[required_cols].to_dict('records')
        print(f"YAHOO FINANCE: Successfully fetched {len(candles)} candles.")
        return candles
    except Exception as e:
        print(f"CRITICAL: Failed to fetch data from yfinance: {e}")
        traceback.print_exc()
        raise

# --- API اینڈ پوائنٹس ---

# --- نیا: Render کے ہیلتھ چیک کے لیے اینڈ پوائنٹ ---
@app.get("/health", status_code=200)
async def health_check():
    """Render کو بتانے کے لیے کہ ایپ زندہ ہے۔"""
    return {"status": "ok"}

@app.get("/api/signal")
async def get_signal(symbol: str = Query("XAU/USD"), timeframe: str = Query("5m")):
    try:
        candles = await fetch_real_ohlc_data(symbol, timeframe)
        if not candles: raise HTTPException(status_code=404, detail="Could not fetch candle data.")
        current_price = candles[-1]['close']
        signal_result = await generate_final_signal(symbol, candles, timeframe)
        signal_result.update({'price': current_price, 'candles': candles})
        log_signal(symbol, signal_result, candles)
        if signal_result.get("signal") in ["buy", "sell"]: add_active_signal(signal_result)
        return signal_result
    except Exception as e:
        print(f"CRITICAL ERROR in get_signal for {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")

# --- بیک گراؤنڈ ٹاسک ---
scheduler = BackgroundScheduler()
def feedback_task_wrapper():
    print("SCHEDULER: Running feedback checker...")
    asyncio.run(check_signals())

@app.on_event("startup")
def startup_event():
    print("STARTUP: Application starting...")
    # scheduler.add_job(feedback_task_wrapper, IntervalTrigger(minutes=15))
    # scheduler.start()

@app.on_event("shutdown")
def shutdown_event():
    print("SHUTDOWN: Application shutting down...")
    # scheduler.shutdown()

# --- اسٹیٹک فائلیں اور روٹ پیج ---
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/", response_class=FileResponse)
async def read_root():
    return 'frontend/index.html'

