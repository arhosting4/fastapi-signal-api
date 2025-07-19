# sentinel.py

import httpx
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# --- سب سے اہم اور حتمی تبدیلی ---
# key_manager کو key_manager.py سے امپورٹ کرنے کی بجائے،
# اسے utils.py سے امپورٹ کریں، جہاں اس کی مثال (instance) بنتی ہے۔
from utils import key_manager

from database_crud import update_news_cache, get_cached_news
from src.database.models import SessionLocal

NEWS_CACHE_DURATION = timedelta(hours=4)
last_news_update = None

async def update_economic_calendar_cache():
    global last_news_update
    print("--- SENTINEL: Updating economic calendar cache... ---")
    
    # اب key_manager براہ راست utils سے آئے گا
    api_key = key_manager.get_api_key()
    if not api_key:
        print("--- SENTINEL ERROR: No API key for news update. ---")
        return

    url = f"https://api.twelvedata.com/economic_calendar?country=US,GB,DE,JP,CN&apikey={api_key}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=20)
        
        if response.status_code == 429:
            key_manager.mark_key_as_limited(api_key)
            return
        
        response.raise_for_status()
        data = response.json()
        
        db = SessionLocal()
        try:
            update_news_cache(db, data)
            last_news_update = datetime.utcnow()
            print("--- SENTINEL: News cache updated successfully. ---")
        finally:
            db.close()

    except Exception as e:
        print(f"--- SENTINEL CRITICAL ERROR: Could not update news cache: {e} ---")

async def get_news_analysis_for_symbol(symbol: str):
    db = SessionLocal()
    try:
        all_events = get_cached_news(db)
        if not all_events or 'events' not in all_events:
            return {"impact": "Clear", "reason": "News cache is empty."}
    finally:
        db.close()

    symbol_base = symbol.split('/')[0]
    high_impact_events = [
        event for event in all_events['events']
        if event.get('importance') == 'high' and symbol_base in event.get('currency', '')
    ]

    if high_impact_events:
        return {"impact": "High", "reason": f"High-impact news for {symbol_base} is scheduled."}
    
    return {"impact": "Clear", "reason": "No high-impact news scheduled for this symbol."}
    
