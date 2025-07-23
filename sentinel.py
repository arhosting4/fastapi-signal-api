# filename: sentinel.py

import httpx
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional, Dict

from utils import key_manager
from database_crud import update_news_cache, get_cached_news
from src.database.models import SessionLocal

async def fetch_from_twelve_data(client: httpx.AsyncClient) -> Optional[Dict]:
    """Twelve Data سے خبریں حاصل کرنے کی کوشش کرتا ہے۔"""
    api_key = key_manager.get_twelve_data_api_key()
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
        print(f"--- SENTINEL INFO: Failed to fetch from Twelve Data: {e} ---")
        return None

async def fetch_from_marketaux(client: httpx.AsyncClient) -> Optional[Dict]:
    """MarketAux سے خبریں حاصل کرنے کی کوشش کرتا ہے۔"""
    api_key = key_manager.get_marketaux_api_key()
    if not api_key:
        return None
        
    url = f"https://api.marketaux.com/v1/news/all?symbols=TSLA,AMZN,MSFT,GOOGL&filter_entities=true&language=en&api_token={api_key}"
    try:
        response = await client.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        if 'data' in data:
            articles = [{
                'title': item.get('title'),
                'url': item.get('url'),
                'source': item.get('source')
            } for item in data['data']]
            return {"articles": articles}
        return None
    except Exception as e:
        print(f"--- SENTINEL INFO: Failed to fetch from MarketAux: {e} ---")
        return None

async def update_economic_calendar_cache():
    """ایک دوہری پرت والے نظام کا استعمال کرتے ہوئے مارکیٹ کی خبروں کو اپ ڈیٹ کرتا ہے۔"""
    print("--- SENTINEL: Updating news cache (Dual-Source Mode)... ---")
    news_data = None
    async with httpx.AsyncClient() as client:
        print("--- SENTINEL: Attempting to fetch news from Twelve Data... ---")
        news_data = await fetch_from_twelve_data(client)
        
        if not news_data:
            print("--- SENTINEL: Twelve Data failed. Falling back to MarketAux... ---")
            news_data = await fetch_from_marketaux(client)

    if news_data and 'articles' in news_data:
        db = SessionLocal()
        try:
            update_news_cache(db, news_data)
            print("--- SENTINEL: News cache updated successfully. ---")
        finally:
            db.close()
    else:
        print("--- SENTINEL CRITICAL ERROR: Both news sources failed. Could not update news cache. ---")

async def get_news_analysis_for_symbol(symbol: str):
    """کیش شدہ خبروں کی بنیاد پر کسی مخصوص علامت کے لیے خبروں کے اثرات کا تجزیہ کرتا ہے۔"""
    db = SessionLocal()
    try:
        all_news = get_cached_news(db)
        if not all_news or 'articles' not in all_news or not all_news['articles']:
            return {"impact": "Clear", "reason": "News cache is empty or has no articles."}
    finally:
        db.close()

    symbol_base = symbol.split('/')[0].upper()
    high_impact_keywords = ['rate', 'inflation', 'cpi', 'fed', 'ecb', 'boj', 'unemployment', 'war', 'crisis']
    
    for article in all_news['articles']:
        title = article.get('title', '').lower()
        if symbol_base.lower() in title or any(keyword in title for keyword in high_impact_keywords):
            return {
                "impact": "High",
                "reason": f"Potentially high-impact news found: '{article.get('title', '')[:50]}...'"
            }
            
    return {"impact": "Clear", "reason": "No high-impact news scheduled for this symbol."}
