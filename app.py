import os
import httpx
import traceback
import asyncio
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import yfinance as yf
import pandas as pd

# --- AI اور ہیلپر ماڈیولز کو امپورٹ کریں ---
from fusion_engine import generate_final_signal
from logger import log_signal
# --- فنکشن کا صحیح نام امپورٹ کریں ---
from feedback_checker import check_signals 
from signal_tracker import add_active_signal

# --- FastAPI ایپ اور شیڈولر کی شروعات ---
app = FastAPI()
scheduler = BackgroundScheduler()

# --- ہیلپر فنکشنز ---

def get_yfinance_symbol(symbol: str) -> str:
    """عام سمبل کو yfinance کے فارمیٹ میں تبدیل کرتا ہے۔"""
    if symbol.upper() == "XAU/USD":
        return "GC=F"
    return symbol

async def fetch_real_ohlc_data(symbol: str, timeframe: str):
    """yfinance کا استعمال کرتے ہوئے OHLC ڈیٹا حاصل کرتا ہے۔"""
    yfinance_symbol = get_yfinance_symbol(symbol)
    
    period_map = {
        "1m": "2d", "5m": "5d", "15m": "10d",
        "1h": "1mo", "4h": "3mo", "1d": "1y"
    }
    period = period_map.get(timeframe, "5d")

    print(f"YAHOO FINANCE: '{yfinance_symbol}' کا ڈیٹا ({timeframe}, {period}) حاصل کیا جا رہا ہے...")

    try:
        data = await asyncio.to_thread(
            yf.download,
            tickers=yfinance_symbol,
            period=period,
            interval=timeframe,
            progress=False
        )

        if data.empty:
            raise ValueError(f"'{yfinance_symbol}' کے لیے کوئی ڈیٹا نہیں ملا۔")

        data.reset_index(inplace=True)
        
        data.rename(columns={"Datetime": "dt"}, inplace=True)
        data['dt'] = pd.to_datetime(data['dt'], utc=True)

        data.rename(columns={
            "dt": "datetime", "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume"
        }, inplace=True)

        data['datetime'] = data['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')

        candles = data.to_dict('records')
        print(f"YAHOO FINANCE: کامیابی سے {len(candles)} کینڈلز حاصل کی گئیں۔")
        return candles

    except Exception as e:
        print(f"CRITICAL: yfinance سے ڈیٹا حاصل کرنے میں ناکامی: {e}")
        traceback.print_exc()
        raise

# --- API اینڈ پوائنٹس ---

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

@app.get("/")
async def read_root():
    return FileResponse('frontend/index.html')

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/signal")
async def get_signal(
    symbol: str = Query("XAU/USD", description="Trading symbol"),
    timeframe: str = Query("5m", description="Chart timeframe")
):
    try:
        candles = await fetch_real_ohlc_data(symbol, timeframe)
        
        if not candles:
            raise HTTPException(status_code=404, detail="Could not fetch candle data.")

        current_price = candles[-1]['close']
        signal_result = await generate_final_signal(symbol, candles, timeframe)

        signal_result['price'] = current_price
        signal_result['candles'] = candles
        
        log_signal(symbol, signal_result, candles)

        if signal_result.get("signal") in ["buy", "sell"]:
            add_active_signal(signal_result)

        return signal_result

    except Exception as e:
        print(f"CRITICAL ERROR in get_signal for {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")


# --- بیک گراؤنڈ ٹاسک ---
def feedback_task_wrapper():
    """async فنکشن کو چلانے کے لیے ایک ریپر۔"""
    print("SCHEDULER: فیڈ بیک چیکر چل رہا ہے...")
    # --- فنکشن کا صحیح نام استعمال کریں ---
    asyncio.run(check_signals()) 

# --- ایپ کے شروع اور بند ہونے پر ---
@app.on_event("startup")
def startup_event():
    """ایپ کے شروع ہونے پر شیڈولر کو شروع کرتا ہے۔"""
    print("STARTUP: ایپلیکیشن شروع ہو رہی ہے...")
    scheduler.add_job(feedback_task_wrapper, IntervalTrigger(minutes=15))
    scheduler.start()

@app.on_event("shutdown")
def shutdown_event():
    """ایپ کے بند ہونے پر شیڈولر کو بند کرتا ہے۔"""
    print("SHUTDOWN: ایپلیکیشن بند ہو رہی ہے...")
    scheduler.shutdown()
    
