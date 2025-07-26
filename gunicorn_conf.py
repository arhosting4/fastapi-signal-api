# filename: gunicorn_conf.py

import asyncio
import logging
from multiprocessing import current_process

# لاگنگ کی بنیادی ترتیب
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')
logging.getLogger('apscheduler').setLevel(logging.WARNING) # شیڈیولر کو خاموش کریں

def when_ready(server):
    """
    یہ فنکشن Gunicorn کے ماسٹر پروسیس کے شروع ہونے پر صرف ایک بار چلتا ہے۔
    """
    logging.info("Gunicorn ماسٹر پروسیس تیار ہے۔ ورکرز شروع کیے جا رہے ہیں۔")

def post_fork(server, worker):
    """
    یہ فنکشن ہر ورکر کے بننے کے بعد چلتا ہے۔
    ہم پس منظر کے کام صرف پہلے ورکر (worker 1) پر چلائیں گے۔
    """
    # صرف پہلے ورکر پر پس منظر کے کام شروع کریں
    if current_process().pid == worker.pid:
        logging.info(f"پہلا ورکر (PID: {worker.pid}) شروع ہو رہا ہے۔ پس منظر کے کام شروع کیے جا رہے ہیں۔")
        
        # مقامی امپورٹس تاکہ وہ صرف اسی ورکر میں لوڈ ہوں
        from app import startup_background_tasks
        
        # ایک نیا ایونٹ لوپ بنائیں اور پس منظر کے کام چلائیں
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(startup_background_tasks())
        loop.close()
    else:
        logging.info(f"اضافی ورکر (PID: {worker.pid}) شروع ہو رہا ہے۔ کوئی پس منظر کا کام نہیں ہے۔")
