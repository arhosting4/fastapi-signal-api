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
from config import HIGH_IMPACT_KEYWORDS

logger = logging.getLogger(__name__)

MARKETAUX_API_KEY = os.getenv("MARKETAUX_API_KEY")

async def fetch_news_from_marketaux(client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    """MarketAux سے خبریں حاصل کرتا ہے۔"""
    if not MARKETAUX_API_KEY:
        logger.error("MarketAux API کی کلید (MARKETAUX_API_KEY) ماحول کے متغیرات میں سیٹ نہیں ہے۔")
        return None
        
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
    """
    مارکیٹ کی خبروں کو اپ ڈیٹ کرتا ہے اور انہیں علامت کے لحاظ سے گروپ کرکے ڈیٹا بیس میں کیش کرتا ہے۔
    """
    logger.info(">>> خبروں کا کیش اپ ڈیٹ کرنے کا کام شروع ہو رہا ہے...")
    
    async with httpx.AsyncClient() as client:
        news_data = await fetch_news_from_marketaux(client)

    if news_data and 'data' in news_data and news_data['data']:
        categorized_articles = {}
        
        for item in news_data['data']:
            title = item.get('title', '').lower()
            snippet = item.get('snippet', '').lower()
            content = title + " " + snippet
            
            impact = "Low"
            for currency, keywords in HIGH_IMPACT_KEYWORDS.items():
                if any(keyword in content for keyword in keywords):
                    impact = "High"
                    break

            article_data = {
                'title': item.get('title'),
                'url': item.get('url'),
                'source': item.get('source'),
                'snippet': item.get('snippet'),
                'published_at': item.get('published_at'),
                'impact': impact,
                'entities': [entity.get('symbol') for entity in item.get('entities', [])]
            }
            
            for entity_symbol in article_data['entities']:
                if entity_symbol not in categorized_articles:
                    categorized_articles[entity_symbol] = []
                categorized_articles[entity_symbol].append(article_data)
        
        db = SessionLocal()
        try:
            update_news_cache_in_db(db, {"articles_by_symbol": categorized_articles})
            logger.info(f"خبروں کا کیش کامیابی سے {len(categorized_articles)} علامتوں کے لیے اپ ڈیٹ ہو گیا۔")
        finally:
            db.close()
    else:
        logger.warning("MarketAux سے کوئی خبر نہیں ملی یا جواب خالی تھا۔ کیش اپ ڈیٹ نہیں ہوا۔")

async def get_news_analysis_for_symbol(symbol: str) -> Dict[str, Any]:
    """
    کیش شدہ خبروں کی بنیاد پر کسی مخصوص علامت کے لیے خبروں کے اثرات کا تیزی سے تجزیہ کرتا ہے۔
    """
    db = SessionLocal()
    try:
        all_news_content = get_cached_news(db)
        if not all_news_content or 'articles_by_symbol' not in all_news_content:
            return {"impact": "Clear", "reason": "خبروں کا کیش خالی یا غلط فارمیٹ میں ہے۔"}
    finally:
        db.close()

    symbol_parts = [s.strip() for s in symbol.upper().split('/')]
    
    relevant_articles = []
    for part in symbol_parts:
        relevant_articles.extend(all_news_content['articles_by_symbol'].get(part, []))
    
    if not relevant_articles:
        return {"impact": "Clear", "reason": "اس علامت کے لیے کوئی متعلقہ خبر نہیں ملی۔"}

    now = datetime.utcnow()
    
    for article in relevant_articles:
        if article.get('impact') != "High":
            continue

        try:
            published_time_str = article.get('published_at')
            if not published_time_str: continue
            if 'Z' not in published_time_str and '+' not in published_time_str:
                 published_time_str += 'Z'
            published_time = datetime.fromisoformat(published_time_str.replace('Z', '+00:00'))
            
            if now - timedelta(hours=1) <= published_time.replace(tzinfo=None) <= now + timedelta(hours=4):
                return {
                    "impact": "High",
                    "reason": f"ایک اعلیٰ اثر والی خبر ملی: '{article.get('title', '')[:60]}...'"
                }
        except Exception as e:
            logger.warning(f"خبر کی تاریخ پارس کرنے میں خرابی: {e} - '{article.get('published_at')}'")
            
    return {"impact": "Clear", "reason": "اس علامت کے لیے کوئی حالیہ یا آنے والی اعلیٰ اثر والی خبر نہیں ملی۔"}

async def check_news_at_time_of_trade(symbol: str, trade_start_time: datetime, trade_end_time: datetime) -> bool:
    """
    یہ چیک کرتا ہے کہ آیا کسی ٹریڈ کے دوران کوئی اعلیٰ اثر والی خبر جاری ہوئی تھی۔
    """
    db = SessionLocal()
    try:
        all_news_content = get_cached_news(db)
        if not all_news_content or 'articles_by_symbol' not in all_news_content:
            return False
    finally:
        db.close()

    symbol_parts = [s.strip() for s in symbol.upper().split('/')]
    
    relevant_articles = []
    for part in symbol_parts:
        relevant_articles.extend(all_news_content['articles_by_symbol'].get(part, []))
    
    if not relevant_articles:
        return False

    for article in relevant_articles:
        if article.get('impact') != "High":
            continue

        try:
            published_time_str = article.get('published_at')
            if not published_time_str: continue
            
            if 'Z' not in published_time_str and '+' not in published_time_str:
                 published_time_str += 'Z'
            published_time = datetime.fromisoformat(published_time_str.replace('Z', '+00:00')).replace(tzinfo=None)
            
            if trade_start_time <= published_time <= trade_end_time:
                logger.info(f"ٹریڈ {symbol} کے دوران ایک اعلیٰ اثر والی خبر ملی: '{article.get('title', '')[:60]}...'")
                return True
        except Exception as e:
            logger.warning(f"خبر کی تاریخ پارس کرنے میں خرابی: {e} - '{article.get('published_at')}'")
            
    return False
    
