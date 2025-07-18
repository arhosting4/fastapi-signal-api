import asyncio
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- اہم تبدیلیاں: feedback_checker سے صحیح فنکشن امپورٹ کریں ---
from feedback_checker import check_active_signals_job
from fusion_engine import generate_final_signal
from signal_tracker import get_active_signal_for_timeframe, add_active_signal
# (باقی تمام ضروری امپورٹس جیسے yfinance, pandas, os, traceback)
import yfinance as yf
import pandas as pd

app = FastAPI(title="ScalpMaster AI API")

# --- شیڈیولر کی شروعات ---
scheduler = AsyncIOScheduler(timezone="UTC")

@app.on_event("startup")
async def startup_event():
    """ ایپ شروع ہوتے ہی شیڈیولر کو شروع کرتا ہے۔ """
    # جاب کو ہر 60 سیکنڈ بعد چلانے کے لیے شیڈول کریں
    scheduler.add_job(check_active_signals_job, 'interval', seconds=60, id="signal_check_job")
    scheduler.start()
    print("APScheduler started. The signal checker job is now running every 60 seconds.")

@app.on_event("shutdown")
async def shutdown_event():
    """ ایپ بند ہوتے ہی شیڈیولر کو روکتا ہے۔ """
    scheduler.shutdown()
    print("APScheduler has been shut down.")

# (باقی تمام کوڈ جیسے get_yfinance_symbol, fetch_real_ohlc_data, اور API اینڈ پوائنٹس ویسے ہی رہیں گے)
def get_yfinance_symbol(symbol: str) -> str:
    if symbol.upper() == "XAU/USD": return "GC=F"
    return symbol

async def fetch_real_ohlc_data(symbol: str, timeframe: str):
    yfinance_symbol = get_yfinance_symbol(symbol)
    period_map = {"1m": "2d", "5m": "5d", "15m": "10d"}
    period = period_map.get(timeframe)
    if not period: raise ValueError(f"Unsupported timeframe: {timeframe}")
    print(f"YAHOO FINANCE: Fetching data for '{yfinance_symbol}' ({timeframe}, {period})...")
    try:
        data = await asyncio.to_thread(
            yf.download, tickers=yfinance_symbol, period=period, interval=timeframe,
            progress=False, auto_adjust=False
        )
        if data.empty: raise ValueError(f"No data returned for '{yfinance_symbol}'.")
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        data.reset_index(inplace=True)
        data.columns = [str(col).lower().strip() for col in data.columns]
        rename_dict = {'date': 'datetime', 'index': 'datetime'}
        data.rename(columns=rename_dict, inplace=True)
        required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in data.columns: raise ValueError(f"Missing required column '{col}'.")
        data['datetime'] = pd.to_datetime(data['datetime']).dt.tz_convert('UTC').dt.strftime('%Y-%m-%d %H:%M:%S')
        return data[required_cols].to_dict('records')
    except Exception as e:
        print(f"CRITICAL: Failed to process data from yfinance: {e}")
        traceback.print_exc()
        raise

@app.get("/health", status_code=200, tags=["System"])
async def health_check():
    return {"status": "ok", "message": "ScalpMaster AI is running."}

@app.get("/api/signal", tags=["AI Signals"])
async def get_signal(symbol: str = Query("XAU/USD"), timeframe: str = Query("5m")):
    try:
        active_signal = get_active_signal_for_timeframe(symbol, timeframe)
        if active_signal:
            print(f"Returning existing active signal {active_signal.get('id')}.")
            active_signal.pop('candles', None) 
            candles = await fetch_real_ohlc_data(symbol, timeframe)
            active_signal['candles'] = candles
            return active_signal

        print(f"No active signal found for {symbol} on {timeframe}. Generating a new one.")
        candles = await fetch_real_ohlc_data(symbol, timeframe)
        if not candles or len(candles) < 34:
            raise HTTPException(status_code=404, detail="Not enough historical data for a new signal.")
        
        signal_result = await generate_final_signal(symbol, candles, timeframe)
        
        if signal_result.get("signal") in ["buy", "sell"]:
            add_active_signal(signal_result)
        
        return signal_result
        
    except Exception as e:
        print(f"CRITICAL SERVER ERROR in get_signal for {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
                      
