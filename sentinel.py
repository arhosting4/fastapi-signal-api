# filename: sentinel.py

import os
import httpx
import asyncio
import logging
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List

# مقامی امپورٹس
from database_crud import update_news_cache, get_cached_news
from models import SessionLocal

logger = logging.getLogger(__name__)

# ==============================================================================
# ★★★ حتمی نیوز سسٹم ★★★
# ==============================================================================

# MarketAux API کی کلید کو ماحول کے متغیرات سے حاصل کریں
MARKETAUX_API_KEY = os.getenv("MARKETAUX_API_KEY")

async def fetch_news_from_marketaux(client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    """MarketAux سے خبریں حاصل کرتا ہے۔"""
    if not MARKETAUX_API_KEY:
        logger.error("MarketAux API کی کلید (MARKETAUX_API_KEY) ماحول کے متغیرات میں سیٹ نہیں ہے۔")
        return None
        
    # اہم اسٹاکس اور فاریکس کے لیے علامتیں
    url = f"https://api.marketaux.com/v1/news/all?symbols=TSLA,AMZN,MSFT,GOOGL,XAU,EUR,GBP,BTC&filter_entities=true&language=en&limit=50&api_token={MARKETAUX_API_KEY}"
    
    try:
        logger.info("MarketAux API سے خبریں حاصل کی جا رہی ہیں...")
        response = await client.get(url, timeout=20)
        response.raise_for_status()  # HTTP خرابیوں کے لیے ایکسیپشن اٹھائیں
        data = response.json()
        logger.info("MarketAux API سے کامیابی سے خبریں حاصل کی گئیں۔")
        return data

    except httpx.HTTPStatusError as e:
        logger.error(f"MarketAux API سے HTTP خرابی: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"MarketAux سے خبریں حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
        return None

async def update_economic_calendar_cache():
    """مارکیٹ کی خبروں کو اپ ڈیٹ کرتا ہے اور انہیں ڈیٹا بیس میں کیش کرتا ہے۔"""
    logger.info(">>> خبروں کا کیش اپ ڈیٹ کرنے کا کام شروع ہو رہا ہے...")
    
    async with httpx.AsyncClient() as client:
        news_data = await fetch_news_from_marketaux(client)

    if news_data and 'data' in news_data and news_data['data']:
        # MarketAux کے جواب کو ہمارے مطلوبہ فارمیٹ میں تبدیل کریں
        articles = [{
            'title': item.get('title'),
            'url': item.get('url'),
            'source': item.get('source'),
            'snippet': item.get('snippet'),
            'published_at': item.get('published_at'),
        } for item in news_data['data']]
        
        db = SessionLocal()
        try:
            # صرف خبروں کے مواد کو محفوظ کریں
            update_news_cache(db, {"articles": articles})
            logger.info(f"خبروں کا کیش کامیابی سے {len(articles)} مضامین کے ساتھ اپ ڈیٹ ہو گیا۔")
        finally:
            db.close()
    else:
        logger.warning("MarketAux سے کوئی خبر نہیں ملی یا جواب خالی تھا۔ کیش اپ ڈیٹ نہیں ہوا۔")

async def get_news_analysis_for_symbol(symbol: str) -> Dict[str, Any]:
    """کیش شدہ خبروں کی بنیاد پر کسی مخصوص علامت کے لیے خبروں کے اثرات کا تجزیہ کرتا ہے۔"""
    db = SessionLocal()
    try:
        all_news_content = get_cached_news(db)
        if not all_news_content or 'articles' not in all_news_content or not all_news_content['articles']:
            return {"impact": "Clear", "reason": "خبروں کا کیش خالی ہے۔"}
    finally:
        db.close()

    symbol_base = symbol.split('/')[0].upper()
    high_impact_keywords = ['rate', 'inflation', 'cpi', 'fed', 'ecb', 'boj', 'unemployment', 'war', 'crisis', 'nfp']
    
    for article in all_news_content['articles']:
        title = article.get('title', '').lower()
        # علامت اور کلیدی الفاظ دونوں کو چیک کریں
        if symbol_base.lower() in title or any(keyword in title for keyword in high_impact_keywords):
            return {
                "impact": "High",
                "reason": f"ممکنہ طور پر زیادہ اثر والی خبر ملی: '{article.get('title', '')[:60]}...'"
            }
            
    return {"impact": "Clear", "reason": "اس علامت کے لیے کوئی زیادہ اثر والی خبر نہیں ملی۔"}

