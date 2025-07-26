# filename: scheduler.py
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# --- درست امپورٹس ---
from hunter import hunt_for_signals_job
from feedback_checker import check_active_signals_job
from sentinel import update_economic_calendar_cache

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_scheduler() -> AsyncIOScheduler:
    """ایک نیا شیڈیولر بناتا اور کنفیگر کرتا ہے۔"""
    scheduler = AsyncIOScheduler(timezone="UTC")
    try:
        # ملازمتوں کو ان کے درست فنکشن ناموں کے ساتھ شامل کریں
        scheduler.add_job(hunt_for_signals_job, IntervalTrigger(minutes=5), id='hunt_for_signals')
        scheduler.add_job(check_active_signals_job, IntervalTrigger(minutes=1), id='check_active_signals')
        scheduler.add_job(update_economic_calendar_cache, IntervalTrigger(hours=4), id='update_news')
        logger.info("شیڈیولر کی ملازمتیں کامیابی سے کنفیگر ہو گئیں۔")
    except Exception as e:
        logger.error(f"شیڈیولر کی ملازمتیں شامل کرنے میں خرابی: {e}")
    return scheduler

# یہ فنکشنز app.py سے کال کیے جا سکتے ہیں
def start_scheduler(scheduler: AsyncIOScheduler):
    """شیڈیولر شروع کرتا ہے۔"""
    if not scheduler.running:
        scheduler.start()
        logger.info("شیڈیولر شروع ہو گیا۔")

def shutdown_scheduler(scheduler: AsyncIOScheduler):
    """شیڈیولر کو احسن طریقے سے بند کرتا ہے۔"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("شیڈیولر احسن طریقے سے بند ہو گیا۔")
        
