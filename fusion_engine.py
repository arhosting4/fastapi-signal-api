import os
import traceback
import asyncio
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import yfinance as yf
import pandas as pd

# --- اہم تبدیلی: اصل فیوژن انجن کو امپورٹ کریں ---
from fusion_engine import generate_final_signal

# --- FastAPI ایپ کی شروعات ---
app = FastAPI()

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
        
        # ملٹی انڈیکس کالمز کو ہینڈل کریں
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
        
        # تاریخ کو UTC میں تبدیل کریں اور فارمیٹ کریں
        data['datetime'] = pd.to_datetime(data['datetime']).dt.tz_convert('UTC').dt.strftime('%Y-%m-%d %H:%M:%S')
        
        candles = data[required_cols].to_dict('records')
        print(f"YAHOO FINANCE: Successfully fetched and processed {len(candles)} candles.")
        return candles
    except Exception as e:
        print(f"CRITICAL: Failed to process data from yfinance: {e}")
        traceback.print_exc()
        raise

# --- API اینڈ پوائنٹس ---

@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

@app.get("/api/signal")
async def get_signal(symbol: str = Query("XAU/USD"), timeframe: str = Query("5m")):
    try:
        # 1. ڈیٹا حاصل کریں
        candles = await fetch_real_ohlc_data(symbol, timeframe)
        if not candles: 
            raise HTTPException(status_code=404, detail="Could not fetch candle data.")
        
        # 2. --- اہم تبدیلی: اصل AI انجن کو کال کریں ---
        signal_result = await generate_final_signal(symbol, candles, timeframe)
        
        # 3. نتیجہ واپس بھیجیں
        return signal_result
        
    except Exception as e:
        print(f"CRITICAL ERROR in get_signal for {symbol}: {e}")
        traceback.print_exc()
        # فرنٹ اینڈ کو ایک واضح ایرر بھیجیں
        raise HTTPException(status_code=500, detail=f"AI Engine Error: {str(e)}")

# --- اسٹیٹک فائلیں اور روٹ پیج ---
# یہ لائن 'frontend' فولڈر میں موجود تمام فائلوں کو پیش کرے گی
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

