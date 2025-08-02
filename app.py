# filename: app.py

from fastapi import FastAPI, WebSocket
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

from models import Base, engine
from hunter import run_hunter_engine      # This must be the async function from hunter.py
from feedback_checker import run_guardian_engine   # Also an async function
from websocket_manager import manager as ws_manager

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# --- DB Table Creation (startup only) ---
@app.on_event("startup")
async def on_startup():
    Base.metadata.create_all(bind=engine)
    logging.info("📊 Database tables ensured/created (models.py).")

    scheduler = AsyncIOScheduler()
    scheduler.start()
    # Signal generation cycle (“Hunter” job)
    scheduler.add_job(run_hunter_engine, 'interval', minutes=3, id="hunter_job")
    # Monitoring/TP-SL trigger (“Guardian” job)
    scheduler.add_job(run_guardian_engine, 'interval', minutes=1, id="guardian_job")
    app.state.scheduler = scheduler
    logging.info("⏲️ APScheduler jobs started: hunter/guardian.")

@app.on_event("shutdown")
async def on_shutdown():
    scheduler = getattr(app.state, 'scheduler', None)
    if scheduler:
        scheduler.shutdown()
        logging.info("Scheduler stopped.")

# --- Example WebSocket Route (matches frontend index.html) ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await ws_manager.broadcast({"echo": data})
    except Exception:
        ws_manager.disconnect(websocket)

# --- Healthcheck Route/Example REST route ---
@app.get("/health")
async def healthcheck():
    return {"status": "ok"}

# 🚩 اگر آپ کو فرنٹ اینڈ کے لیے سگنل ہسٹری یا خبروں کی REST فیڈ چاہیے:
# (add these routes if needed for history.html/news.html)

# from fastapi import Depends
# from sqlalchemy.orm import Session
# from models import SessionLocal, ActiveSignal, NewsCache

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# @app.get("/api/signal-history")
# def get_signal_history(db: Session = Depends(get_db)):
#     # Replace with your logic for fetching closed signals from DB
#     return []

# @app.get("/api/news-feed")
# def get_news_feed(db: Session = Depends(get_db)):
#     # Replace with your news cache fetching logic
#     return []

# --- مزید custom REST/WebSocket endpoints یہاں add کریں ---

