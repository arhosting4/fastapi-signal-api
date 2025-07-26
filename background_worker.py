# filename: background_worker.py

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# ... (باقی امپورٹس ویسے ہی رہیں گے) ...
from feedback_checker import price_stream_logic, check_active_signals_job
from hunter import hunt_for_signals_job
from sentinel import update_economic_calendar_cache
from models import create_db_and_tables

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [BG_WORKER] - %(message)s')
logger = logging.getLogger(__name__)

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# ★★★ نیا "نگران" فنکشن جو صرف یہ بتائے گا کہ سسٹم زندہ ہے ★★★
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
def system_heartbeat_job():
    """یہ جاب صرف یہ تصدیق کرنے کے لیے ہے کہ شیڈیولر زندہ ہے۔"""
    logger.info("❤️ سسٹم ہارٹ بیٹ: تمام پس منظر کے کام فعال ہیں۔ مارکیٹ کے مواقع کا انتظار ہے۔")

async def main():
    logger.info(">>> پس منظر کا ورکر (Background Worker) شروع ہو رہا ہے...")
    create_db_and_tables()
    logger.info("ڈیٹا بیس کی حالت کی تصدیق ہو گئی۔")

    scheduler = AsyncIOScheduler(timezone="UTC")
    
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    # ★★★ نئی "نگران" جاب کو شیڈیولر میں شامل کریں ★★★
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    scheduler.add_job(system_heartbeat_job, IntervalTrigger(minutes=5), id="system_heartbeat")
    
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=5), id="hunt_for_signals")
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), id="check_active_signals")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="update_news")
    
    scheduler.start()
    logger.info("★★★ شیڈیولر کامیابی سے شروع ہو گیا۔ ★★★")

    await price_stream_logic()

if __name__ == "__main__":
    asyncio.run(main())
    
