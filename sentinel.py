# filename: sentinel.py

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

import httpx
from sqlalchemy.orm import Session

# مقامی امپورٹس
from database_crud import update_news_cache_in_db, get_cached_news
from models import SessionLocal
# مرکزی کنفیگریشن ماڈیولز سے سیٹنگز درآمد کریں
from config import api_settings, news_settings, trading_settings

logger = logging.getLogger(__name__)

# --- کنفیگریشن سے مستقل اقدار ---
MARKETAUX_API_KEY = api_settings.MARKETAUX_API_KEY
HIGH_IMPACT_KEYWORDS = news_settings.HIGH_IMPACT_KEYWORDS

def _get_news_symbols() -> str:
    """
    کنفیگریشن سے تمام ٹریڈنگ جوڑوں کو اکٹھا کرکے ایک منفرد علامتوں کی فہرست بناتا ہے۔
    """
    all_pairs = (
        trading_settings.WEEKDAY_PRIMARY +
        trading_settings.WEEKDAY_BACKUP +
        trading_settings.WEEKEND_PRIMARY +
        trading_settings.WEEKEND_BACKUP
    )
    
    unique_symbols = set()
    for pair in all_pairs:
        parts = pair.split('/')
        unique_symbols.update(p.strip() for p in parts)
        
    # اضافی اہم علامتیں شامل کریں
    unique_symbols.update(['TSLA', 'AMZN', 'MSFT', 'GOOGL'])
    
    return ",".join(sorted(list(unique_symbols)))

async def _fetch_news_from_marketaux(client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    """MarketAux API سے تازہ ترین خبریں حاصل کرتا ہے۔"""
    if not MARKETAUX_API_KEY:
        logger.error("MarketAux API کی کلید (MARKETAUX_API_KEY) سیٹ نہیں ہے۔ خبریں حاصل نہیں کی جا سکتیں۔")
        return None
        
    symbols_str = _get_news_symbols()
    url = (f"https://api.marketaux.com/v1/news/all?symbols={symbols_str}"
           f"&filter_entities=true&language=en&limit=100&api_token={MARKETAUX_API_KEY}")
    
    try:
        logger.info("MarketAux API سے خبریں حاصل کی جا رہی ہیں...")
        response = await client.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
        logger.info(f"MarketAux API سے کامیابی سے {len(data.get('data', []))} خبریں حاصل کی گئیں۔")
        return data
    except httpx.HTTPStatusError as e:
        logger.error(f"MarketAux API سے HTTP خرابی: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"MarketAux سے خبریں حاصل کرنے میں غیر متوقع خرابی: {e}", exc_info=True)
    
    return None

async def update_economic_calendar_cache():
    """
    مارکیٹ کی خبروں کو اپ ڈیٹ کرتا ہے اور انہیں علامت کے لحاظ سے گروپ کرکے ڈیٹا بیس میں کیش کرتا ہے۔
    """
    logger.info("📰 خبروں کا کیش اپ ڈیٹ کرنے کا کام شروع ہو رہا ہے...")
    
    async with httpx.AsyncClient() as client:
        news_data = await _fetch_news_from_marketaux(client)

    if not (news_data and 'data' in news_data and news_data['data']):
        logger.warning("MarketAux سے کوئی خبر نہیں ملی یا جواب خالی تھا۔ کیش اپ ڈیٹ نہیں ہوا۔")
        return

    categorized_articles = {}
    for item in news_data['data']:
        title = item.get('title', '').lower()
        snippet = item.get('snippet', '').lower()
        content = f"{title} {snippet}"
        
        impact = "Low"
        # اعلیٰ اثر والے مطلوبہ الفاظ کی بنیاد پر اثر کا تعین کریں
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
        logger.info(f"📰 خبروں کا کیش کامیابی سے {len(categorized_articles)} علامتوں کے لیے اپ ڈیٹ ہو گیا۔")
    finally:
        db.close()

def _parse_datetime_string(datetime_str: str) -> Optional[datetime]:
    """
    مختلف فارمیٹس میں آنے والی تاریخ کی سٹرنگ کو محفوظ طریقے سے پارس کرتا ہے
    اور اسے ٹائم زون سے آگاہ (timezone-aware) UTC datetime آبجیکٹ میں تبدیل کرتا ہے۔
    """
    if not datetime_str:
        return None
    try:
        # ISO 8601 فارمیٹ کو ہینڈل کرنے کی کوشش کریں
        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        # اگر ٹائم زون کی معلومات نہ ہوں تو اسے UTC سمجھیں
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        logger.warning(f"خبر کی تاریخ کو پارس نہیں کیا جا سکا: '{datetime_str}'")
        return None

async def get_news_analysis_for_symbol(symbol: str) -> Dict[str, Any]:
    """
    کیش شدہ خبروں کی بنیاد پر کسی مخصوص علامت کے لیے خبروں کے اثرات کا تیزی سے تجزیہ کرتا ہے۔
    """
    db = SessionLocal()
    try:
        all_news_content = get_cached_news(db)
        if not (all_news_content and 'articles_by_symbol' in all_news_content):
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
            
        # چیک کریں کہ آیا خبر حال ہی میں (پچھلے 1 گھنٹے میں) جاری ہوئی ہے
        # یا جلد ہی (اگلے 4 گھنٹوں میں) آنے والی ہے
        if now_utc - timedelta(hours=1) <= published_time <= now_utc + timedelta(hours=4):
            return {
                "impact": "High",
                "reason": f"ایک اعلیٰ اثر والی خبر ملی: '{article.get('title', '')[:60]}...'"
            }
            
    return {"impact": "Clear", "reason": "اس علامت کے لیے کوئی حالیہ یا آنے والی اعلیٰ اثر والی خبر نہیں ملی۔"}

async def check_news_at_time_of_trade(symbol: str, trade_start_time: datetime, trade_end_time: datetime) -> bool:
    """
    یہ چیک کرتا ہے کہ آیا کسی ٹریڈ کے دوران کوئی اعلیٰ اثر والی خبر جاری ہوئی تھی۔
    """
    db = SessionLocal()
    try:
        all_news_content = get_cached_news(db)
        if not (all_news_content and 'articles_by_symbol' in all_news_content):
            return False
    finally:
        db.close()

    symbol_parts = [s.strip().upper() for s in symbol.split('/')]
    
    relevant_articles = []
    for part in symbol_parts:
        relevant_articles.extend(all_news_content['articles_by_symbol'].get(part, []))
    
    if not relevant_articles:
        return False

    # ٹریڈ کے اوقات کو ٹائم زون سے آگاہ بنائیں (UTC)
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
    
