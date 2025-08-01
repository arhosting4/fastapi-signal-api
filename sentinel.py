# filename: sentinel.py

import os
import httpx
import asyncio
import logging
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone

# مقامی امپورٹس
from database_crud import update_news_cache_in_db, get_cached_news
from models import SessionLocal
from config import HIGH_IMPACT_KEYWORDS

logger = logging.getLogger(__name__)
MARKETAUX_API_KEY = os.getenv("MARKETAUX_API_KEY")

# =====================================================================================
async def fetch_news_from_marketaux(client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    """
    MarketAux API سے خبریں حاصل کرتا ہے
    """
    if not MARKETAUX_API_KEY:
        logger.error("❌ MarketAux API کلید نہیں ملی (MARKETAUX_API_KEY)")
        return None

    url = (
        f"https://api.marketaux.com/v1/news/all"
        f"?symbols=TSLA,AMZN,MSFT,GOOGL,XAU,EUR,GBP,JPY,CHF,CAD,AUD,NZD,BTC,ETH"
        f"&filter_entities=true&language=en&limit=100"
        f"&api_token={MARKETAUX_API_KEY}"
    )

    try:
        logger.info("🌐 MarketAux API سے خبریں حاصل کی جا رہی ہیں...")
        response = await client.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
        logger.info(f"✅ {len(data.get('data', []))} خبریں کامیابی سے حاصل ہو گئیں")
        return data
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP خرابی: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"❌ خبریں حاصل کرنے میں خرابی: {e}", exc_info=True)
    return None

# =====================================================================================
def check_news_at_time_of_trade(db: Session, symbol: str, trade_time: datetime) -> str:
    """
    دیے گئے symbol اور وقت پر نیوز امپیکٹ چیک کرتا ہے۔
    """
    try:
        cached = get_cached_news(db)
        news_list = cached.get("data", []) if cached else []

        impact_found = "none"
        window = timedelta(minutes=30)
        for item in news_list:
            try:
                pub_time = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00"))
                if abs(pub_time - trade_time) <= window:
                    title = item.get("title", "").lower()
                    if any(keyword.lower() in title for keyword in HIGH_IMPACT_KEYWORDS):
                        impact_found = "positive" if "gain" in title or "up" in title else "negative"
                        break
            except Exception as e:
                logger.warning(f"⚠️ ایک نیوز item کو parse کرنے میں خرابی: {e}")
        return impact_found
    except Exception as e:
        logger.error(f"❌ نیوز چیک کرتے وقت خرابی: {e}", exc_info=True)
        return "none"

# =====================================================================================
async def refresh_news_and_cache():
    """
    MarketAux API سے خبریں حاصل کرتا ہے اور DB میں cache کرتا ہے
    """
    try:
        async with httpx.AsyncClient() as client:
            news_data = await fetch_news_from_marketaux(client)
            if news_data:
                db: Session = SessionLocal()
                update_news_cache_in_db(db, news_data)
                db.close()
    except Exception as e:
        logger.error(f"❌ Cache refresh کرتے وقت خرابی: {e}", exc_info=True)
