import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .hunter import hunt_for_signals
from .feedback_checker import check_active_signals
from .sentinel import update_economic_calendar_cache

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

scheduler = AsyncIOScheduler()

def start_scheduler():
    """Adds jobs to the scheduler and starts it."""
    try:
        scheduler.add_job(hunt_for_signals, 'interval', minutes=5, id='hunt_for_signals_job')
        scheduler.add_job(check_active_signals, 'interval', minutes=1, id='check_active_signals_job')
        scheduler.add_job(update_economic_calendar_cache, 'interval', hours=4, id='update_calendar_job')
        scheduler.start()
        logging.info("Scheduler started with jobs.")
    except Exception as e:
        logging.error(f"Error starting scheduler: {e}")

def shutdown_scheduler():
    """Shuts down the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown()
        logging.info("Scheduler shut down gracefully.")
      
