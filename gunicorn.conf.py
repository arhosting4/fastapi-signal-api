# filename: gunicorn.conf.py
from os import environ

# ورکرز کی تعداد (Render کے مفت پلان کے لیے 2 بہتر ہے)
workers = int(environ.get('GUNICORN_WORKERS', '2'))
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
bind = f"0.0.0.0:{environ.get('PORT', '8000')}"
accesslog = "-"
errorlog = "-"

def on_starting(server):
    """Gunicorn ماسٹر پروسیس شروع ہونے پر صرف ایک بار شیڈیولر شروع کریں"""
    from app import scheduler
    if not scheduler.running:
        try:
            scheduler.start()
            server.log.info("APScheduler کامیابی سے ماسٹر پروسیس میں شروع ہو گیا۔")
        except Exception as e:
            server.log.error(f"APScheduler شروع کرنے میں ناکام: {e}")

def on_exit(server):
    """Gunicorn بند ہونے پر شیڈیولر کو صاف ستھرے طریقے سے بند کریں"""
    from app import scheduler
    if scheduler.running:
        scheduler.shutdown()
        server.log.info("APScheduler کامیابی سے بند ہو گیا۔")
      
