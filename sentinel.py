import logging
import httpx
import asyncio
from datetime import datetime

# براہ راست امپورٹس
from database_config import SessionLocal
import database_crud as crud
import utils

async def get_news_analysis_for_symbol(symbol: str) -> dict:
    """
    Provides a simple news analysis for a given symbol.
    For now, it just checks if there is any high-impact news.
    """
    db = SessionLocal()
    try:
        news_cache = crud.get_cached_news(db)
        if news_cache and news_cache.content and news_cache.content.get('data'):
            # A more sophisticated analysis could be done here
            return {"impact": "High", "summary": "High-impact news present."}
        return {"impact": "Low", "summary": "No high-impact news."}
    finally:
        db.close()

async def update_economic_calendar_cache():
    """
    Fetches the latest high-impact news from MarketAux and caches it.
    """
    logging.info("Attempting to update economic calendar cache...")
    api_key = utils.get_marketaux_api_key()
    if not api_key:
        logging.warning("MarketAux API key not found. Skipping news update.")
        return

    url = f"https://api.marketaux.com/v1/news/all?symbols=TSLA,AMZN,MSFT&filter_entities=true&language=en&api_token={api_key}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=20.0)
            response.raise_for_status()
            news_data = response.json()
            
            db = SessionLocal()
            try:
                crud.update_news_cache(db, news_data=news_data)
                logging.info("Successfully updated news cache.")
            finally:
                db.close()

        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP error fetching news from MarketAux: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logging.error(f"An error occurred while updating news cache: {e}", exc_info=True)

