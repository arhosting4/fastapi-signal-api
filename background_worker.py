# filename: background_worker.py

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# مقامی امپورٹس
from feedback_checker import price_stream_logic, check_active_signals_job
from hunter import hunt_for_signals_job
from sentinel import update_economic_calendar_cache
from models import create_db_and_tables

# لاگنگ سیٹ اپ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [BG_WORKER] - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    logger.info(">>> پس منظر کا ورکر (Background Worker) شروع ہو رہا ہے...")

    # 1. ڈیٹا بیس بنائیں (صرف ایک بار)
    create_db_and_tables()
    logger.info("ڈیٹا بیس کی حالت کی تصدیق ہو گئی۔")

    # 2. شیڈیولر شروع کریں
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=5), id="hunt_for_signals")
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), id="check_active_signals")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="update_news")
    scheduler.start()
    logger.info("★★★ شیڈیولر کامیابی سے شروع ہو گیا۔ ★★★")

    # 3. ریئل ٹائم پرائس سٹریم شروع کریں اور اسے ہمیشہ چلنے دیں
    # یہ اس بات کو یقینی بنائے گا کہ ورکر بند نہ ہو
    await price_stream_logic()

if __name__ == "__main__":
    asyncio.run(main())
