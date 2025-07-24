# filename: utils.py
import httpx
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict

import config
from key_manager import key_manager
from schemas import TwelveDataTimeSeries

logger = logging.getLogger(__name__)

def get_available_pairs() -> List[str]:
    """ہفتے کے دن کی بنیاد پر مارکیٹ کے دستیاب جوڑے واپس کرتا ہے۔"""
    today = datetime.utcnow().weekday()
    # ہفتہ (5) اور اتوار (6) کو صرف کرپٹو
    if today >= 5:
        return config.AVAILABLE_PAIRS_WEEKEND
    return config.AVAILABLE_PAIRS_WEEKDAY

async def fetch_twelve_data_ohlc(symbol: str, timeframe: str, size: int) -> Optional[List[Dict]]:
    """
    TwelveData API سے OHLC کینڈلز لاتا ہے۔ اگر کلید کی حد ہو جائے تو گھوماتا ہے۔
    """
    api_key = key_manager.get_api_key()
    if not api_key:
        logger.error("کوئی دستیاب Twelve Data API کلید نہیں ملی۔")
        return None
    
    url = (
        f"https://api.twelvedata.com/time_series"
        f"?symbol={symbol}&interval={timeframe}&outputsize={size}&apikey={api_key}"
    )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        
        if response.status_code == 429:
            logger.warning(f"API کلید ...{api_key[-4:]} کے لیے شرح کی حد تک پہنچ گئی۔ کلید کو گھمایا جا رہا ہے۔")
            key_manager.mark_key_as_limited(api_key)
            await asyncio.sleep(1)
            return await fetch_twelve_data_ohlc(symbol, timeframe, size)
        
        response.raise_for_status()
        data = response.json()
        
        # Pydantic کے ساتھ ڈیٹا کی توثیق کریں
        validated_data = TwelveDataTimeSeries(**data)
        
        # ڈیٹا کو الٹا کریں تاکہ تازہ ترین کینڈل آخر میں ہو
        return [c.dict() for c in reversed(validated_data.values)]

    except Exception as e:
        logger.error(f"{symbol} کے لیے OHLC ڈیٹا حاصل کرنے میں ناکام: {e}", exc_info=True)
        return None

async def get_current_price_twelve_data(symbol: str, client: httpx.AsyncClient) -> Optional[float]:
    """کسی جوڑے کی موجودہ قیمت حاصل کرتا ہے۔"""
    api_key = key_manager.get_api_key()
    if not api_key:
        logger.error("موجودہ قیمت حاصل کرنے کے لیے کوئی دستیاب API کلید نہیں ہے۔")
        return None

    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={api_key}"
    try:
        response = await client.get(url, timeout=10)
        
        if response.status_code == 429:
            key_manager.mark_key_as_limited(api_key)
            await asyncio.sleep(1)
            return await get_current_price_twelve_data(symbol, client)
            
        response.raise_for_status()
        data = response.json()
        price = data.get("price")
        
        if price:
            return float(price)
        logger.warning(f"{symbol} کے لیے قیمت کے جواب میں 'price' کلید نہیں ہے۔")
        return None
    except Exception as e:
        logger.error(f"{symbol} کے لیے موجودہ قیمت حاصل کرنے میں ناکام: {e}", exc_info=True)
        return None
        
