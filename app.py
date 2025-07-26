# filename: app.py

import asyncio
import logging
from fastapi import FastAPI, Depends
# ... (دیگر امپورٹس)

# لاگنگ کی ترتیب اب gunicorn_conf.py میں ہے
logger = logging.getLogger(__name__)

app = FastAPI(title="ScalpMaster AI API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ... (API روٹس اور get_db فنکشن ویسے ہی رہیں گے) ...

# ★★★ اہم تبدیلی: ایک نیا فنکشن جو پس منظر کے کاموں کو شروع کرتا ہے ★★★
async def startup_background_tasks():
    """
    یہ فنکشن صرف پہلے ورکر پر gunicorn_conf.py کے ذریعے چلایا جائے گا۔
    """
    logger.info("پس منظر کے کاموں کی ترتیب شروع کی جا رہی ہے...")
    
    # مقامی امپورٹس
    from price_stream import start_price_websocket
    from hunter import hunt_for_signals_job
    from feedback_checker import check_active_signals_job
    from sentinel import update_economic_calendar_cache
    from models import create_db_and_tables
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    # DB اور پرائس سٹریم شروع کریں
    create_db_and_tables()
    asyncio.create_task(start_price_websocket())
    await update_economic_calendar_cache()

    # شیڈیولر شروع کریں
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=5), id="hunt_for_signals")
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), id="check_active_signals")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="update_news")
    # نوٹ: واچ ڈاگ کی اب ضرورت نہیں کیونکہ ہم جانتے ہیں کہ صرف ایک پرائس سٹریم ہے
    scheduler.start()
    
    logger.info("★★★ پس منظر کے تمام کام اور شیڈیولر کامیابی سے شروع ہو گئے۔ ★★★")
    
    # اس فنکشن کو ہمیشہ چلتے رہنے دیں تاکہ پس منظر کے کام چلتے رہیں
    while True:
        await asyncio.sleep(3600) # ایک گھنٹے کے لیے سو جائیں

# ★★★ اہم تبدیلی: @app.on_event("startup") کو مکمل طور پر ہٹا دیا گیا ہے ★★★

# ... (باقی کوڈ جیسے shutdown_event اور سٹیٹک فائلز ویسے ہی رہیں گے) ...
