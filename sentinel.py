# filename: sentinel.py

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

# مقامی امپورٹس
from database_crud import get_cached_news, update_news_cache_in_db
from models import SessionLocal
# اصلاح: 'news_settings' کو صحیح طریقے سے امپورٹ کیا گیا
from config import api_settings, news_settings

logger = logging.getLogger(__name__)

MARKETAUX_API_KEY = api_settings.MARKETAUX_API_KEY
HIGH_IMPACT_KEYWORDS = news_settings.HIGH_IMPACT_KEYWORDS

async def fetch_news_from_marketaux(client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    """MarketAux API سے تازہ ترین خبریں حاصل کرتا ہے۔"""
    if not MARKETAUX_API_KEY:
        logger.error("MarketAux API کی کلید (MARKETAUX_API_KEY) ماحول کے متغیرات میں سیٹ نہیں ہے۔")
        return None
    
    # علامتوں کی ایک وسیع رینج کے لیے خبریں حاصل کریں
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
    """خبروں کو حاصل کرتا ہے، ان کی درجہ بندی کرتا ہے، اور ڈیٹا بیس میں کیش کرتا ہے۔"""
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
            
            # کلیدی الفاظ کی بنیاد پر خبر کے اثر کا تعین کریں
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
            
            # خبر کو اس سے متعلقہ تمام علامتوں کے تحت محفوظ کریں
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

def _parse_datetime_string(datetime_str: str) -> Optional[datetime]:
    """مختلف فارمیٹس کی تاریخ/وقت کی سٹرنگ کو UTC datetime آبجیکٹ میں تبدیل کرتا ہے۔"""
    if not datetime_str:
        return None
    try:
        # ٹائم زون کی معلومات کے ساتھ ISO 8601 فارمیٹ کو ہینڈل کریں
        if 'Z' in datetime_str or '+' in datetime_str or '-' in datetime_str[10:]:
            dt_aware = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return dt_aware.astimezone(timezone.utc)
        else:
            # بغیر ٹائم زون کے فارمیٹ کو UTC سمجھیں
            dt_naive = datetime.fromisoformat(datetime_str)
            return dt_naive.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError) as e:
        logger.warning(f"خبر کی تاریخ پارس کرنے میں خرابی: {e} - '{datetime_str}'")
        return None

async def get_news_analysis_for_symbol(symbol: str) -> Dict[str, Any]:
    """کسی مخصوص علامت کے لیے حالیہ یا آنے والی اعلیٰ اثر والی خبروں کا تجزیہ کرتا ہے۔"""
    db = SessionLocal()
    try:
        all_news_content = get_cached_news(db)
        if not all_news_content or 'articles_by_symbol' not in all_news_content:
            return {"impact": "Clear", "reason": "خبروں کا کیش خالی یا غلط فارمیٹ میں ہے۔"}
    finally:
        db.close()
        
    symbol_parts = [s.strip().upper() for s in symbol.split('/')]
    relevant_articles = []
    for part in symbol_parts:
        relevant_articles.extend(all_news_content['articles_by_symbol'].get(part, []))
        
    if not relevant_articles:
        return {"impact": "Clear", "reason": "اس علامت کے لیے کوئی متعلقہ خبر نہیں ملی۔"}
        
    now_utc = datetime.now(timezone.utc)
    for article in relevant_articles:
        if article.get('impact') != "High":
            continue
            
        published_time = _parse_datetime_string(article.get('published_at'))
        if not published_time:
            continue
            
        # چیک کریں کہ آیا خبر پچھلے 1 گھنٹے سے لے کر اگلے 4 گھنٹے کے اندر ہے
        if now_utc - timedelta(hours=1) <= published_time <= now_utc + timedelta(hours=4):
            return {
                "impact": "High",
                "reason": f"ایک اعلیٰ اثر والی خبر ملی: '{article.get('title', '')[:60]}...'"
            }
            
    return {"impact": "Clear", "reason": "اس علامت کے لیے کوئی حالیہ یا آنے والی اعلیٰ اثر والی خبر نہیں ملی۔"}

async def check_news_at_time_of_trade(symbol: str, trade_start_time: datetime, trade_end_time: datetime) -> bool:
    """چیک کرتا ہے کہ آیا کسی ٹریڈ کے دوران کوئی اعلیٰ اثر والی خبر جاری ہوئی تھی۔"""
    db = SessionLocal()
    try:
        all_news_content = get_cached_news(db)
        if not all_news_content or 'articles_by_symbol' not in all_news_content:
            return False
    finally:
        db.close()
        
    symbol_parts = [s.strip().upper() for s in symbol.split('/')]
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
            logger.info(f"ٹریڈ {symbol} کے دوران ایک اعلیٰ اثر والی خبر ملی: '{article.get('title', '')[:60]}...'")
            return True
            
    return False
    
