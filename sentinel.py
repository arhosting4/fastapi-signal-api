# filename: sentinel.py

import os
import httpx
import asyncio
import logging
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

# مقامی امپورٹس
from database_crud import update_news_cache_in_db, get_cached_news
from models import SessionLocal

logger = logging.getLogger(__name__)

MARKETAUX_API_KEY = os.getenv("MARKETAUX_API_KEY")

# ★★★ نیا: اعلیٰ اثر والے اقتصادی واقعات کے لیے مطلوبہ الفاظ ★★★
# ان الفاظ کو کرنسی کے ناموں کے ساتھ ملا کر تلاش کیا جائے گا
HIGH_IMPACT_KEYWORDS = {
    'USD': ['fed', 'fomc', 'cpi', 'nfp', 'unemployment', 'inflation', 'gdp', 'powell'],
    'EUR': ['ecb', 'inflation', 'gdp', 'unemployment', 'lagarde'],
    'GBP': ['boe', 'inflation', 'gdp', 'unemployment', 'bailey'],
    'XAU': ['war', 'crisis', 'geopolitical', 'fed', 'inflation'], # سونا اکثر عالمی واقعات سے متاثر ہوتا ہے
    'BTC': ['sec', 'regulation', 'etf', 'crypto ban', 'halving']
}

async def fetch_news_from_marketaux(client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    """MarketAux سے خبریں حاصل کرتا ہے۔"""
    if not MARKETAUX_API_KEY:
        logger.error("MarketAux API کی کلید (MARKETAUX_API_KEY) ماحول کے متغیرات میں سیٹ نہیں ہے۔")
        return None
        
    # ہم تمام اہم کرنسیوں اور اثاثوں سے متعلق خبریں حاصل کر رہے ہیں
    url = f"https://api.marketaux.com/v1/news/all?symbols=TSLA,AMZN,MSFT,GOOGL,XAU,EUR,GBP,JPY,CHF,CAD,AUD,NZD,BTC,ETH&filter_entities=true&language=en&limit=100&api_token={MARKETAUX_API_KEY}"
    
    try:
        logger.info("MarketAux API سے خبریں حاصل کی جا رہی ہیں...")
        response = await client.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
        logger.info(f"MarketAux API سے کامیابی سے {len(data.get('data', []))} خبریں حاصل کی گئیں۔")
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
        # ★★★ اب ہم خبروں کے ساتھ ان کی اہمیت بھی محفوظ کریں گے ★★★
        articles = []
        for item in news_data['data']:
            title = item.get('title', '').lower()
            snippet = item.get('snippet', '').lower()
            content = title + " " + snippet
            
            impact = "Low"
            # چیک کریں کہ آیا کوئی اعلیٰ اثر والا مطلوبہ لفظ موجود ہے
            for currency, keywords in HIGH_IMPACT_KEYWORDS.items():
                if any(keyword in content for keyword in keywords):
                    impact = "High"
                    break # جیسے ہی ایک اعلیٰ اثر والا لفظ ملے، لوپ توڑ دیں

            articles.append({
                'title': item.get('title'),
                'url': item.get('url'),
                'source': item.get('source'),
                'snippet': item.get('snippet'),
                'published_at': item.get('published_at'),
                'impact': impact, # ★★★ اہمیت کو یہاں محفوظ کیا جا رہا ہے ★★★
                'entities': [entity.get('symbol') for entity in item.get('entities', [])] # متعلقہ علامتیں
            })
        
        db = SessionLocal()
        try:
            update_news_cache_in_db(db, {"articles": articles})
            logger.info(f"خبروں کا کیش کامیابی سے {len(articles)} مضامین کے ساتھ اپ ڈیٹ ہو گیا۔")
        finally:
            db.close()
    else:
        logger.warning("MarketAux سے کوئی خبر نہیں ملی یا جواب خالی تھا۔ کیش اپ ڈیٹ نہیں ہوا۔")

async def get_news_analysis_for_symbol(symbol: str) -> Dict[str, Any]:
    """
    کیش شدہ خبروں کی بنیاد پر کسی مخصوص علامت کے لیے خبروں کے اثرات کا تجزیہ کرتا ہے۔
    ★★★ اب یہ آنے والے واقعات پر زیادہ توجہ دیتا ہے۔ ★★★
    """
    db = SessionLocal()
    try:
        all_news_content = get_cached_news(db)
        if not all_news_content or 'articles' not in all_news_content or not all_news_content['articles']:
            return {"impact": "Clear", "reason": "خبروں کا کیش خالی ہے۔"}
    finally:
        db.close()

    # علامت کے بنیادی اور ثانوی حصے الگ کریں (مثلاً, "EUR/USD" -> "EUR", "USD")
    symbol_parts = symbol.upper().split('/')
    
    now = datetime.utcnow()
    
    for article in all_news_content['articles']:
        # صرف اعلیٰ اثر والی خبروں پر توجہ دیں
        if article.get('impact') != "High":
            continue

        # چیک کریں کہ آیا خبر اس علامت سے متعلق ہے
        is_relevant = any(part in article.get('entities', []) for part in symbol_parts)
        
        if is_relevant:
            published_time = datetime.fromisoformat(article.get('published_at').replace('Z', '+00:00'))
            
            # اگر خبر حال ہی میں شائع ہوئی ہے یا مستقبل قریب میں متوقع ہے
            if now - timedelta(hours=1) <= published_time <= now + timedelta(hours=4):
                return {
                    "impact": "High",
                    "reason": f"ایک اعلیٰ اثر والی خبر ملی: '{article.get('title', '')[:60]}...'"
                }
            
    return {"impact": "Clear", "reason": "اس علامت کے لیے کوئی حالیہ یا آنے والی اعلیٰ اثر والی خبر نہیں ملی۔"}
                                                             
