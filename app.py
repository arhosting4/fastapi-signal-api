import os
import traceback
import asyncio
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
import yfinance as yf
import pandas as pd

# --- اہم: اصل فیوژن انجن کو امپورٹ کریں ---
from fusion_engine import generate_final_signal

# --- FastAPI ایپ کی شروعات ---
app = FastAPI(title="ScalpMaster AI API")

# --- ہیلپر فنکشنز ---
def get_yfinance_symbol(symbol: str) -> str:
    """ 'XAU/USD' جیسے علامات کو yfinance کے لیے 'GC=F' میں تبدیل کرتا ہے۔ """
    if symbol.upper() == "XAU/USD":
        return "GC=F"
    return symbol

async def fetch_real_ohlc_data(symbol: str, timeframe: str):
    """Yahoo Finance سے OHLCV ڈیٹا حاصل کرتا ہے۔"""
    yfinance_symbol = get_yfinance_symbol(symbol)
    
    period_map = {"1m": "2d", "5m": "5d", "15m": "10d", "1h": "1mo", "4h": "3mo", "1d": "1y"}
    period = period_map.get(timeframe)
    if not period:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    print(f"YAHOO FINANCE: Fetching data for '{yfinance_symbol}' (Timeframe: {timeframe}, Period: {period})...")
    
    try:
        data = await asyncio.to_thread(
            yf.download,
            tickers=yfinance_symbol,
            period=period,
            interval=timeframe,
            progress=False,
            auto_adjust=False
        )
        
        if data.empty:
            raise ValueError(f"No data returned from yfinance for '{yfinance_symbol}'.")
        
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        data.reset_index(inplace=True)
        data.columns = [str(col).lower().strip() for col in data.columns]
        
        rename_dict = {'date': 'datetime', 'index': 'datetime'}
        data.rename(columns=rename_dict, inplace=True)
        
        required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"Missing required column '{col}'. Available columns: {data.columns.to_list()}")
        
        data['datetime'] = pd.to_datetime(data['datetime']).dt.tz_convert('UTC').dt.strftime('%Y-%m-%d %H:%M:%S')
        
        candles = data[required_cols].to_dict('records')
        print(f"YAHOO FINANCE: Successfully fetched and processed {len(candles)} candles.")
        return candles
        
    except Exception as e:
        print(f"CRITICAL: Failed to fetch or process data from yfinance: {e}")
        traceback.print_exc()
        raise

# --- API اینڈ پوائنٹس ---

@app.get("/health", status_code=200, tags=["System"])
async def health_check():
    """ Render.com جیسی سروسز کے لیے ہیلتھ چیک اینڈ پوائنٹ۔ """
    return {"status": "ok", "message": "ScalpMaster AI is running."}

@app.get("/api/signal", tags=["AI Signals"])
async def get_signal(symbol: str = Query("XAU/USD", description="Trading Symbol"), timeframe: str = Query("5m", description="Chart Timeframe (e.g., 1m, 5m, 15m)")):
    """
    ایک مخصوص علامت اور ٹائم فریم کے لیے AI ٹریڈنگ سگنل تیار کرتا ہے۔
    """
    try:
        candles = await fetch_real_ohlc_data(symbol, timeframe)
        if not candles or len(candles) < 20:
            raise HTTPException(status_code=404, detail="Not enough historical data to generate a reliable signal.")
        
        print(f"Invoking AI Fusion Engine for {symbol} on {timeframe} timeframe...")
        signal_result = await generate_final_signal(symbol, candles, timeframe)
        print(f"AI Engine returned signal: {signal_result.get('signal')}")
        
        return signal_result
        
    except ValueError as ve:
        print(f"VALUE ERROR in get_signal: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"CRITICAL SERVER ERROR in get_signal for {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred in the AI Engine: {str(e)}")

# --- اسٹیٹک فائلیں اور روٹ پیج ---
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
