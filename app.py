import os
import traceback
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from typing import Dict, Any

# ہمارے پروجیکٹ کے ماڈیولز
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache
from signal_tracker import get_live_signal, add_active_signal
# کلید مینیجر کو یہاں امپورٹ کرنے کی ضرورت نہیں، کیونکہ دیگر ماڈیولز اسے استعمال کرتے ہیں

app = FastAPI(title="ScalpMaster AI - Hunter Edition v2 (Resilient)")

# یہ کیشے اب صرف چارٹ کی قیمت کے لیے ہے، جو کہ اب استعمال نہیں ہو رہا،
# لیکن مستقبل میں کام آ سکتا ہے۔
price_cache: Dict[str, Any] = {}
CACHE_DURATION_SECONDS = 30

# شیڈیولر جو ہماری پس منظر کی تمام جابز کو چلائے گا
scheduler = AsyncIOScheduler(timezone="UTC")

@app.on_event("startup")
async def startup_event():
    """
    سرور شروع ہونے پر پس منظر کی تمام جابز کو ترتیب دیتا اور شروع کرتا ہے۔
    """
    print("--- ScalpMaster AI Engine: Initializing Startup Sequence ---")
    
    # سرور شروع ہوتے ہی ایک بار نیوز کیشے کو فوری اپ ڈیٹ کریں تاکہ تازہ ترین ڈیٹا موجود ہو
    await update_economic_calendar_cache()

    # 1. سگنل ہنٹر جاب (ہر 10 منٹ)
    # یہ وقفہ ہمیں 3 API کلیدوں کے ساتھ 2400 کالز کی یومیہ حد کے اندر رکھتا ہے (تقریباً 1728 کالز)
    scheduler.add_job(hunt_for_signals_job, 'interval', minutes=10, id="hunter_job")
    
    # 2. TP/SL نگران جاب (ہر 10 منٹ اور 5 سیکنڈ)
    # اسے تھوڑا سا آفسیٹ دیا گیا ہے تاکہ یہ ہنٹر کے ساتھ ایک ہی وقت پر نہ چلے
    scheduler.add_job(check_active_signals_job, 'interval', minutes=10, seconds=5, id="checker_job")
    
    # 3. نیوز کیشے اپڈیٹر (ہر 12 گھنٹے)
    # یہ انتہائی موثر ہے اور دن میں صرف 2 API کالز استعمال کرتا ہے
    scheduler.add_job(update_economic_calendar_cache, 'interval', hours=12, id="news_updater_job")
    
    scheduler.start()
    
    print("--- ScalpMaster AI Hunter Engine Started Successfully ---")
    print("Scheduler is running the following jobs:")
    print(" -> Signal Hunter: Every 10 minutes")
    print(" -> TP/SL Checker: Every 10 minutes & 5 seconds")
    print(" -> News Updater: Every 12 hours")

@app.on_event("shutdown")
async def shutdown_event():
    """سرور بند ہونے پر شیڈیولر کو صاف طریقے سے بند کرتا ہے۔"""
    scheduler.shutdown()
    print("--- ScalpMaster AI Hunter Engine Shut Down ---")

@app.get("/health", status_code=200, tags=["System"])
async def health_check():
    """یہ یقینی بناتا ہے کہ سرور چل رہا ہے (Render.com کے لیے اہم)۔"""
    return {"status": "ok", "message": "ScalpMaster AI Hunter is running."}

@app.get("/api/get_live_signal", tags=["AI Hunter"])
async def get_current_signal():
    """
    پس منظر میں AI ہنٹر کے ذریعے پائے جانے والے بہترین لائیو سگنل کو فوری طور پر واپس کرتا ہے۔
    یہ کوئی نئی API کال نہیں کرتا، صرف محفوظ کردہ فائل کو پڑھتا ہے۔
    """
    try:
        live_signal = get_live_signal()
        # جب صارف سگنل دیکھتا ہے، تب ہی اسے فعال ٹریکر میں شامل کریں تاکہ TP/SL کی نگرانی شروع ہو
        if live_signal and live_signal.get("signal") in ["buy", "sell"]:
            add_active_signal(live_signal)
        return live_signal
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching live signal: {e}")

# یہ اینڈ پوائنٹ اب براہ راست استعمال نہیں ہو رہا، لیکن مستقبل کے لیے رکھا گیا ہے
@app.get("/api/price", tags=["Real-time Data (Legacy)"])
async def get_realtime_price(symbol: str = Query("XAU/USD")):
    """چارٹ کے لیے قیمت حاصل کرتا ہے (کیشنگ کے ساتھ)۔"""
    now = datetime.utcnow()
    if symbol in price_cache:
        cached_price, cache_time = price_cache[symbol]
        if now - cache_time < timedelta(seconds=CACHE_DURATION_SECONDS):
            return {"symbol": symbol, "price": cached_price, "source": "cache"}
    
    # یہ فنکشن اب براہ راست کلید مینیجر استعمال نہیں کرتا، بلکہ utils کے ذریعے کرے گا
    # اگر اسے دوبارہ فعال کیا جائے تو utils.py میں ایک نیا فنکشن بنانا ہوگا
    raise HTTPException(status_code=404, detail="This endpoint is currently not in active use.")

# اسٹیٹک فائلوں (index.html, وغیرہ) کو پیش کرنے کے لیے
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
