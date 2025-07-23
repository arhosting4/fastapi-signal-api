import sys
import os
import logging
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path # Import pathlib

# --- CRITICAL FIX for Deployment ---
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# --- Define the base directory for the frontend ---
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

# --- Corrected Imports for your file structure ---
from src.database import database_crud as crud, models
import database_config
import scheduler
import api_schemas

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create all database tables on startup
try:
    models.Base.metadata.create_all(bind=database_config.engine)
    logging.info("Database tables checked/created successfully.")
except Exception as e:
    logging.error(f"Error creating database tables: {e}")

app = FastAPI(
    title="ScalpMaster AI API", 
    version="2.2.0", # Final Production Version
    description="A high-performance API for AI-driven scalping signals."
)

# --- Dependency ---
def get_db():
    db = database_config.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Scheduler Events ---
@app.on_event("startup")
def startup_event():
    scheduler.start_scheduler()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown_scheduler()

# --- API Endpoints (No changes here) ---
@app.get("/health", status_code=200, tags=["System"])
def health_check():
    return {"status": "ok", "message": "API is running"}

# ... (باقی تمام API اینڈ پوائنٹس ویسے ہی رہیں گے) ...
@app.get("/api/live-signals", response_model=List[api_schemas.ActiveSignal], tags=["Data"])
def get_live_signals(db: Session = Depends(get_db)):
    return crud.get_all_active_signals(db)

@app.get("/api/history", response_model=List[api_schemas.TradeHistory], tags=["Data"])
def get_trade_history(limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_completed_trades(db, limit=limit)

@app.get("/api/news", response_model=Optional[api_schemas.News], tags=["Data"])
def get_latest_news(db: Session = Depends(get_db)):
    news = crud.get_cached_news(db)
    if not news or not news.get('data'):
        return {"message": "No high-impact news available at the moment."}
    return news

@app.get("/api/summary", response_model=api_schemas.Summary, tags=["Data"])
def get_summary_data(db: Session = Depends(get_db)):
    return crud.get_summary_stats(db)


# --- Static Files and Root Endpoint ---
# This is the final and correct way to serve a Single Page Application (SPA) style frontend

# This will serve files like main.css and main.js from their respective folders
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")

# This will serve the main index.html for the root URL
@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_path = FRONTEND_DIR / "index.html"
    with open(index_path) as f:
        return HTMLResponse(content=f.read(), status_code=200)

# This will serve the other HTML pages
@app.get("/{page_name}", response_class=HTMLResponse)
async def read_page(page_name: str):
    # Basic security to prevent directory traversal
    if ".." in page_name or not page_name.endswith(".html"):
        index_path = FRONTEND_DIR / "index.html"
        with open(index_path) as f:
            return HTMLResponse(content=f.read(), status_code=200)
    
    file_path = FRONTEND_DIR / page_name
    if file_path.exists():
        with open(file_path) as f:
            return HTMLResponse(content=f.read(), status_code=200)
    
    # Fallback to index.html if page not found
    index_path = FRONTEND_DIR / "index.html"
    with open(index_path) as f:
        return HTMLResponse(content=f.read(), status_code=404)

