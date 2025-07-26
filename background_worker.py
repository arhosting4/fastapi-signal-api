# filename: background_worker.py

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta

# مقامی امپورٹس
from feedback_checker import price_stream_logic, check_active_signals_job
from hunter import hunt_for_signals_job
from sentinel import update_economic_calendar_cache
from models import create_db_and_tables

# لاگنگ سیٹ اپ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [BG_WORKER] - %(message)s')
logger = logging.getLogger(__name__)

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# ★★★ یہ وہ تمام کام ہیں جو شیڈیولر کے ذریعے چلائے جائیں گے ★★★
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

def system_heartbeat_job():
    """یہ جاب صرف یہ تصدیق کرنے کے لیے ہے کہ شیڈیولر زندہ ہے۔"""
    logger.info("❤️ سسٹم ہارٹ بیٹ: تمام پس منظر کے کام فعال ہیں۔ مارکیٹ کے مواقع کا انتظار ہے۔")

async def run_price_stream_job():
    """پرائس سٹریم کو ایک محفوظ جاب کے طور پر چلاتا ہے۔"""
    try:
        # ہم اسے 55 سیکنڈ کا ٹائم آؤٹ دیتے ہیں تاکہ یہ ہمیشہ کے لیے نہ پھنسے
        await asyncio.wait_for(price_stream_logic(), timeout=55.0)
    except asyncio.TimeoutError:
        # یہ ایک متوقع نتیجہ ہے، کیونکہ پرائس سٹریم ہمیشہ چلتا رہتا ہے
        logger.info("پرائس سٹریم جاب نے اپنا 55 سیکنڈ کا وقت مکمل کر لیا۔ اگلی بار دوبارہ چلے گی۔")
    except Exception as e:
        logger.error(f"پرائس سٹریم جاب میں خرابی: {e}", exc_info=True)

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# ★★★ ناقابلِ کریش مین فنکشن ★★★
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

async def main():
    logger.info(">>> پس منظر کا ورکر (Background Worker) شروع ہو رہا ہے...")
    
    # 1. ڈیٹا بیس بنائیں (صرف ایک بار)
    try:
        create_db_and_tables()
        logger.info("ڈیٹا بیس کی حالت کی تصدیق ہو گئی۔")
    except Exception as e:
        logger.critical(f"ڈیٹا بیس بنانے میں ناکامی! ورکر شروع نہیں ہو سکتا۔ خرابی: {e}", exc_info=True)
        return

    # 2. شیڈیولر شروع کریں
    scheduler = AsyncIOScheduler(timezone="UTC")
    
    # 3. تمام جابز کو شیڈیولر میں شامل کریں
    scheduler.add_job(system_heartbeat_job, IntervalTrigger(minutes=5), id="system_heartbeat")
    scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=5), id="hunt_for_signals")
    scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), id="check_active_signals")
    scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id="update_news")
    
    # ★★★ پرائس سٹریم کو بھی ایک جاب کے طور پر شامل کریں جو ہر منٹ چلے ★★★
    scheduler.add_job(run_price_stream_job, IntervalTrigger(minutes=1), id="price_stream_job", next_run_time=datetime.now(datetime.UTC))

    scheduler.start()
    logger.info("★★★ شیڈیولر کامیابی سے شروع ہو گیا۔ ★★★")

    # 4. ورکر کو ہمیشہ زندہ رکھنے کے لیے ایک ناقابلِ کریش لوپ
    while True:
        await asyncio.sleep(3600) # ہر گھنٹے بعد جاگو، صرف یہ یقینی بنانے کے لیے کہ لوپ چل رہا ہے

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("پس منظر کا ورکر بند کیا جا رہا ہے۔")
    except Exception as e:
        # یہ حتمی حفاظتی جال ہے
        logger.critical(f"ورکر کی سطح پر مہلک خرابی! ورکر بند ہو رہا ہے۔ خرابی: {e}", exc_info=True)
        
