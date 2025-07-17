import os
import httpx
import traceback
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import yfinance as yf
import pandas as pd

# --- AI اور ہیلپر ماڈیولز کو امپورٹ کریں ---
# (یہ یقینی بنائیں کہ یہ تمام فائلیں آپ کی روٹ ڈائریکٹری میں موجود ہیں)
from fusion_engine import generate_final_signal
from logger import log_signal
from feedback_checker import check_signals_and_give_feedback
from signal_tracker import add_active_signal

# --- FastAPI ایپ اور شیڈولر کی شروعات ---
app = FastAPI()
scheduler = AsyncIOScheduler()

# --- ہیلپر فنکشنز ---

def get_yfinance_symbol(symbol: str) -> str:
    """عام سمبل کو yfinance کے فارمیٹ میں تبدیل کرتا ہے۔"""
    if symbol.upper() == "XAU/USD":
        return "GC=F"  # گولڈ فیوچرز کے لیے yfinance کا سمبل
    # مستقبل میں یہاں مزید پیئرز شامل کیے جا سکتے ہیں
    # مثال کے طور پر:
    # if symbol.upper() == "EUR/USD":
    #     return "EURUSD=X"
    return symbol # اگر کوئی خاص تبدیلی نہیں ہے تو ویسے ہی واپس بھیج دیں

async def fetch_real_ohlc_data(symbol: str, timeframe: str, client: httpx.AsyncClient):
    """yfinance کا استعمال کرتے ہوئے OHLC ڈیٹا حاصل کرتا ہے۔"""
    yfinance_symbol = get_yfinance_symbol(symbol)
    
    # yfinance کے لیے ٹائم فریم اور مدت کو میپ کریں
    # yfinance چھوٹے ٹائم فریمز کے لیے محدود مدت کی اجازت دیتا ہے
    period_map = {
        "1m": "2d",
        "5m": "5d",
        "15m": "10d",
        "1h": "1mo",
        "4h": "3mo",
        "1d": "1y"
    }
    period = period_map.get(timeframe, "5d") # اگر ٹائم فریم نہیں ملتا تو ڈیفالٹ 5 دن

    print(f"YAHOO FINANCE: '{yfinance_symbol}' کا ڈیٹا ({timeframe} ٹائم فریم، {period} کی مدت) حاصل کیا جا رہا ہے...")

    try:
        # yfinance کو ایک الگ تھریڈ میں چلائیں تاکہ یہ async ایونٹ لوپ کو بلاک نہ کرے
        data = await asyncio.to_thread(
            yf.download,
            tickers=yfinance_symbol,
            period=period,
            interval=timeframe,
            progress=False
        )

        if data.empty:
            raise ValueError(f"'{yfinance_symbol}' کے لیے کوئی ڈیٹا نہیں ملا۔")

        # انڈیکس کو ری سیٹ کریں تاکہ 'Datetime' ایک کالم بن جائے
        data.reset_index(inplace=True)
        
        # کالم کے ناموں کو ہمارے معیار کے مطابق بنائیں
        data.rename(columns={
            "Datetime": "datetime",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        }, inplace=True)

        # datetime کو سٹرنگ میں تبدیل کریں تاکہ JSON میں بھیجا جا سکے
        data['datetime'] = data['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')

        # ڈیٹا کو لسٹ آف ڈکشنریز میں تبدیل کریں
        candles = data.to_dict('records')
        print(f"YAHOO FINANCE: کامیابی سے {len(candles)} کینڈلز حاصل کی گئیں۔")
        return candles

    except Exception as e:
        print(f"CRITICAL: yfinance سے ڈیٹا حاصل کرنے میں ناکامی: {e}")
        traceback.print_exc()
        raise

# --- API اینڈ پوائنٹس ---

# فرنٹ اینڈ کو پیش کرنے کے لیے
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

@app.get("/")
async def read_root():
    """HTML فرنٹ اینڈ کو پیش کرتا ہے۔"""
    return FileResponse('frontend/index.html')

@app.get("/health")
def health_check():
    """Render کے ہیلتھ چیک کے لیے اینڈ پوائنٹ۔"""
    return {"status": "ok"}

@app.get("/api/signal")
async def get_signal(
    symbol: str = Query("XAU/USD", description="Trading symbol (e.g., XAU/USD)"),
    timeframe: str = Query("5m", description="Chart timeframe (e.g., 1m, 5m, 15m)")
):
    """AI سگنل، قیمت، اور چارٹ ڈیٹا فراہم کرتا ہے۔"""
    try:
        async with httpx.AsyncClient() as client:
            candles = await fetch_real_ohlc_data(symbol, timeframe, client)
            
            if not candles:
                raise HTTPException(status_code=404, detail="Could not fetch candle data.")

            # آخری کینڈل سے موجودہ قیمت حاصل کریں
            current_price = candles[-1]['close']

            # AI انجن سے سگنل حاصل کریں
            signal_result = await generate_final_signal(symbol, candles, timeframe)

            # نتیجے میں قیمت اور کینڈلز شامل کریں
            signal_result['price'] = current_price
            signal_result['candles'] = candles
            
            # سگنل کو لاگ کریں
            log_signal(symbol, signal_result, candles)

            # اگر سگنل buy/sell ہے تو اسے ٹریکر میں شامل کریں
            if signal_result.get("signal") in ["buy", "sell"]:
                add_active_signal(signal_result)

            return signal_result

    except Exception as e:
        print(f"CRITICAL ERROR in get_signal for {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {e}")


# --- بیک گراؤنڈ ٹاسک ---
@scheduler.scheduled_job(IntervalTrigger(minutes=15))
async def scheduled_feedback_task():
    """ہر 15 منٹ بعد چلنے والا فیڈ بیک چیکر۔"""
    print("SCHEDULER: فیڈ بیک چیکر چل رہا ہے (بیک گراؤنڈ ٹاسک)...")
    await check_signals_and_give_feedback()


# --- ایپ کے شروع اور بند ہونے پر ---
import asyncio

@app.on_event("startup")
async def startup_event():
    """ایپ کے شروع ہونے پر شیڈولر کو شروع کرتا ہے۔"""
    print("STARTUP: ایپلیکیشن شروع ہو رہی ہے...")
    scheduler.start()
    # asyncio.create_task(market_scanner()) # مارکیٹ اسکینر کو مستقبل میں یہاں شامل کیا جائے گا

@app.on_event("shutdown")
def shutdown_event():
    """ایپ کے بند ہونے پر شیڈولر کو بند کرتا ہے۔"""
    print("SHUTDOWN: ایپلیکیشن بند ہو رہی ہے...")
    scheduler.shutdown()

                                    
