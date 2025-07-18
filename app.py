import os
import traceback
import asyncio
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import yfinance as yf
import pandas as pd

# --- FastAPI ایپ کی شروعات ---
app = FastAPI()

# --- فرضی فنکشنز (اگر آپ کے پاس اصل فائلیں نہیں ہیں) ---
async def generate_final_signal(symbol, candles, timeframe):
    if not candles or len(candles) < 2:
        return {"signal": "wait", "reason": "Not enough data."}
    return {
        "signal": "buy" if candles[-1]['close'] > candles[-2]['close'] else "sell",
        "confidence": 75.5, "tier": "Tier 2", "reason": "A test reason.",
        "tp": candles[-1]['close'] * 1.01, "sl": candles[-1]['close'] * 0.99
    }
# --- ختم: فرضی فنکشنز ---

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
        
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        data.reset_index(inplace=True)
        data.columns = [str(col).lower().strip() for col in data.columns]
        
        rename_dict = {'date': 'datetime', 'index': 'datetime'}
        data.rename(columns=rename_dict, inplace=True)
        
        required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"Missing required column '{col}'. Available: {data.columns.to_list()}")
        
        data['datetime'] = pd.to_datetime(data['datetime'], utc=True).dt.strftime('%Y-%m-%d %H:%M:%S')
        candles = data[required_cols].to_dict('records')
        print(f"YAHOO FINANCE: Successfully fetched and processed {len(candles)} candles.")
        return candles
    except Exception as e:
        print(f"CRITICAL: Failed to process data from yfinance: {e}")
        traceback.print_exc()
        raise

# --- API اینڈ پوائنٹس ---

# --- اہم: Render کے ہیلتھ چیک کے لیے اینڈ پوائنٹ ---
@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

@app.get("/api/signal")
async def get_signal(symbol: str = Query("XAU/USD"), timeframe: str = Query("5m")):
    try:
        candles = await fetch_real_ohlc_data(symbol, timeframe)
        if not candles: raise HTTPException(status_code=404, detail="Could not fetch candle data.")
        current_price = candles[-1]['close']
        signal_result = await generate_final_signal(symbol, candles, timeframe)
        signal_result.update({'price': current_price, 'candles': candles})
        return signal_result
    except Exception as e:
        print(f"CRITICAL ERROR in get_signal for {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")

# --- اسٹیٹک فائلیں اور روٹ پیج (سب سے آخر میں) ---
# یہ لائن 'frontend' فولڈر میں موجود تمام فائلوں کو پیش کرے گی
# اور html=True خود بخود index.html کو روٹ پر دکھائے گا
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
        
