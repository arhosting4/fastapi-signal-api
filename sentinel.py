# filename: sentinel.py

import httpx
import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional, Dict, List

# config.py پر انحصار مکمل طور پر ختم کر دیا گیا ہے
# import config
from key_manager import key_manager
from database_crud import update_news_cache, get_cached_news
from models import SessionLocal

logger = logging.getLogger(__name__)

# ==============================================================================
# کنفیگریشن پیرامیٹرز براہ راست یہاں شامل کر دیے گئے ہیں
# ==============================================================================
HIGH_IMPACT_KEYWORDS = ['rate', 'inflation', 'cpi', 'fed', 'ecb', 'boj', 'unemployment', 'war', 'crisis', 'nfp']
# ==============================================================================

async def fetch_from_twelve_data(client: httpx.AsyncClient) -> Optional[Dict]:
    """Twelve Data سے خبریں حاصل کرنے کی کوشش کرتا ہے۔"""
    api_key = key_manager.get_api_key() # اب یہ key_manager سے آتا ہے
    if not api_key:
        return None
    
    url = f"https://api.twelvedata.com/news?source=Reuters,Bloomberg,CNBC&limit=50&apikey={api_key}"
    try:
        response = await client.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and 'articles' in data:
            return data
        elif isinstance(data, list):
            return {"articles": data}
        return None
    except Exception as e:
        logger.error(f"Twelve Data سے خبریں حاصل کرنے میں ناکامی: {e}")
        return None

async def update_economic_calendar_cache():
    """مارکیٹ کی خبروں کو اپ ڈیٹ کرتا ہے۔"""
    logger.info("--- خبروں کا کیش اپ ڈیٹ کیا جا رہا ہے... ---")
    news_data = None
    async with httpx.AsyncClient() as client:
        news_data = await fetch_from_twelve_data(client)

    if news_data and 'articles' in news_data:
        db = SessionLocal()
        try:
            update_news_cache(db, news_data)
            logger.info("--- خبروں کا کیش کامیابی سے اپ ڈیٹ ہو گیا۔ ---")
        finally:
            db.close()
    else:
        logger.critical("--- خبروں کا کوئی ذریعہ کام نہیں کر رہا۔ کیش اپ ڈیٹ کرنے میں ناکام۔ ---")

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
        if symbol_base.lower() in title or any(keyword in title for keyword in HIGH_IMPACT_KEYWORDS):
            return {
                "impact": "High",
                "reason": f"ممکنہ طور پر زیادہ اثر والی خبر ملی: '{article.get('title', '')[:50]}...'"
            }
            
    return {"impact": "Clear", "reason": "اس علامت کے لیے کوئی زیادہ اثر والی خبر نہیں۔"}
    
