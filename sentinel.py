# filename: sentinel.py
import httpx
import asyncio
import logging
import os
from datetime import datetime
from typing import Optional, Dict, List

import config
from database_crud import update_news_cache, get_cached_news
from models import SessionLocal

logger = logging.getLogger(__name__)

MARKETAUX_API_KEY = os.getenv("MARKETAUX_API_KEY")

async def fetch_from_marketaux(client: httpx.AsyncClient) -> Optional[Dict]:
    """MarketAux سے خبریں حاصل کرتا ہے۔"""
    if not MARKETAUX_API_KEY:
        logger.warning("MarketAux API کلید سیٹ نہیں ہے۔ خبریں حاصل کرنا چھوڑ دیا گیا۔")
        return None
        
    url = f"https://api.marketaux.com/v1/news/all?symbols=TSLA,AMZN,MSFT,GOOGL,^GSPC,^DJI&filter_entities=true&language=en&api_token={MARKETAUX_API_KEY}"
    try:
        response = await client.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        if 'data' in data:
            # صرف ضروری فیلڈز کو منتخب کریں
            articles = [{
                'title': item.get('title'),
                'url': item.get('url'),
                'source': item.get('source'),
                'snippet': item.get('snippet'),
                'published_at': item.get('published_at')
            } for item in data['data']]
            return {"articles": articles}
        return None
    except Exception as e:
        logger.error(f"MarketAux سے خبریں حاصل کرنے میں ناکام: {e}", exc_info=True)
        return None

async def update_economic_calendar_cache():
    """مارکیٹ کی خبروں کو اپ ڈیٹ کرتا ہے۔"""
    logger.info("خبروں کا کیش اپ ڈیٹ کیا جا رہا ہے...")
    news_data = None
    async with httpx.AsyncClient() as client:
        news_data = await fetch_from_marketaux(client)

    if news_data and 'articles' in news_data:
        db = SessionLocal()
        try:
            update_news_cache(db, news_data)
            logger.info(f"خبروں کا کیش کامیابی سے اپ ڈیٹ ہو گیا۔ {len(news_data['articles'])} مضامین شامل کیے گئے۔")
        finally:
            db.close()
    else:
        logger.error("خبروں کا کیش اپ ڈیٹ کرنے میں ناکام۔ کوئی ڈیٹا موصول نہیں ہوا۔")

async def get_news_analysis_for_symbol(symbol: str) -> Dict[str, str]:
    """کیش شدہ خبروں کی بنیاد پر کسی مخصوص علامت کے لیے خبروں کے اثرات کا تجزیہ کرتا ہے۔"""
    db = SessionLocal()
    try:
        all_news = get_cached_news(db)
        if not all_news or 'articles' not in all_news or not all_news['articles']:
            return {"impact": "Clear", "reason": "خبروں کا کیش خالی ہے۔"}
    finally:
        db.close()

    symbol_base = symbol.split('/')[0].upper()
    
    for article in all_news['articles']:
        title = article.get('title', '').lower()
        snippet = article.get('snippet', '').lower()
        
        # علامت یا اعلیٰ اثر والے کلیدی الفاظ کی تلاش کریں
        search_text = title + " " + snippet
        if symbol_base.lower() in search_text or any(keyword in search_text for keyword in config.HIGH_IMPACT_KEYWORDS):
            return {
                "impact": "High",
                "reason": f"ممکنہ طور پر اعلیٰ اثر والی خبر ملی: '{article.get('title', '')[:60]}...'"
            }
            
    return {"impact": "Clear", "reason": "اس علامت کے لیے کوئی اعلیٰ اثر والی خبر طے شدہ نہیں ہے۔"}
        
