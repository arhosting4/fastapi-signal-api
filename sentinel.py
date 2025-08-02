# filename: sentinel.py

import os
import httpx
import asyncio
import logging
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone

from database_crud import update_news_cache_in_db, get_cached_news
from models import SessionLocal
from config import HIGH_IMPACT_KEYWORDS

logger = logging.getLogger(__name__)

MARKETAUX_API_KEY = os.getenv("MARKETAUX_API_KEY")

async def fetch_news_from_marketaux(client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    """MarketAux سے خبریں حاصل کرتا ہے (اگر کلید موجود نہ ہو تو None لوٹائے)"""
    if not MARKETAUX_API_KEY:
        logger.error("MarketAux API کی کلید (MARKETAUX_API_KEY) سیٹ نہیں ہے۔")
        return None
    url = (
        "https://api.marketaux.com/v1/news/all?"
        "symbols=TSLA,AMZN,MSFT,GOOGL,XAU,EUR,GBP,JPY,CHF,CAD,AUD,NZD,BTC,ETH"
        "&filter_entities=true&language=en&limit=100"
        f"&api_token={MARKETAUX_API_KEY}"
    )
    try:
        logger.info("MarketAux API سے خبریں حاصل کی جا رہی ہیں...")
        response = await client.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
        logger.info(f"MarketAux API سے {len(data.get('data', []))} خبریں حاصل ہوئیں۔")
        return data
    except httpx.HTTPStatusError as e:
        logger.error(f"MarketAux API سے HTTP خرابی: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"MarketAux سے خبریں حاصل کرنے میں خرابی: {e}", exc_info=True)
        return None

async def update_economic_calendar_cache():
    """خبروں کے ڈیٹا کو fetch، group، اور DB کیش اپڈیٹ کرتا ہے۔"""
    logger.info(">> خبروں کا cache update process شروع ہو رہا ہے...")
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
            logger.info(f"خبروں کا cache {len(categorized_articles)} symbols کیلئے اپڈیٹ ہوا۔")
        finally:
            db.close()
    else:
        logger.warning("MarketAux سے خبر نہ ملی یا جواب خالی۔ Cache update نہیں۔")

def _parse_datetime_string(datetime_str: str) -> Optional[datetime]:
    """String تاریخ کو محفوظ UTC datetime میں بدلتا ہے۔"""
    if not datetime_str:
        return None
    try:
        if 'Z' in datetime_str or '+' in datetime_str or '-' in datetime_str[10:]:
            dt_aware = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return dt_aware.astimezone(timezone.utc)
        else:
            dt_naive = datetime.fromisoformat(datetime_str)
            return dt_naive.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError) as e:
        logger.warning(f"خبر کی تاریخ پارس میں خرابی: {e} - '{datetime_str}'")
        return None

async def get_news_analysis_for_symbol(symbol: str) -> Dict[str, Any]:
    """کیش شدہ DB کی بنیاد پر symbol-specific high-impact news detection."""
    db = SessionLocal()
    try:
        all_news_content = get_cached_news(db)
        if not all_news_content or 'articles_by_symbol' not in all_news_content:
            return {"impact": "Clear", "reason": "خبروں کا cache خالی یا غلط فارمیٹ میں۔"}
    finally:
        db.close()

    symbol_parts = [s.strip() for s in symbol.upper().split('/')]
    relevant_articles = []
    for part in symbol_parts:
        relevant_articles.extend(all_news_content['articles_by_symbol'].get(part, []))
    if not relevant_articles:
        return {"impact": "Clear", "reason": "اس symbol کیلئے کوئی relevant خبر نہیں۔"}
    now_utc = datetime.now(timezone.utc)
    for article in relevant_articles:
        if article.get('impact') != "High":
            continue
        published_time = _parse_datetime_string(article.get('published_at'))
        if not published_time:
            continue
        # پچھلے 1 گھنٹے یا اگلے 4 گھنٹے تک اثر سمجھے
        if now_utc - timedelta(hours=1) <= published_time <= now_utc + timedelta(hours=4):
            return {
                "impact": "High",
                "reason": f"High impact news: '{article.get('title', '')[:60]}...'"
            }
    return {"impact": "Clear", "reason": "کوئی حالیہ high news نہیں۔"}

async def check_news_at_time_of_trade(symbol: str, trade_start_time: datetime, trade_end_time: datetime) -> bool:
    """trade window کے دوران high-impact خبر آئی؟"""
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

    start_time_utc = trade_start_time.replace(tzinfo=timezone.utc)
    end_time_utc = trade_end_time.replace(tzinfo=timezone.utc)
    for article in relevant_articles:
        if article.get('impact') != "High":
            continue
        published_time = _parse_datetime_string(article.get('published_at'))
        if not published_time:
            continue
        if start_time_utc <= published_time <= end_time_utc:
            logger.info(f"ٹریڈ {symbol} کے دوران high-impact خبر: '{article.get('title', '')[:60]}...'")
            return True
    return False
        
