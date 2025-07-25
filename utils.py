# filename: utils.py

import os
import httpx
import asyncio
import logging # <-- لاگنگ امپورٹ کریں
from datetime import datetime
from typing import List, Optional, Dict

from key_manager import KeyManager
from schemas import TwelveDataTimeSeries, Candle

# لاگر سیٹ اپ
logger = logging.getLogger(__name__)

key_manager = KeyManager()

def get_available_pairs() -> List[str]:
    """ہفتے کے دن کی بنیاد پر دستیاب جوڑے واپس کرتا ہے۔"""
    today = datetime.utcnow().weekday()
    # 0-4 سوموار سے جمعہ، 5-6 ہفتہ-اتوار
    if today >= 5: 
        return ["BTC/USD"]
    return ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]

async def fetch_twelve_data_ohlc(symbol: str, timeframe: str, size: int) -> Optional[List[Dict]]:
    """
    TwelveData API سے OHLC کینڈلز لاتا ہے اور API کال کو لاگ کرتا ہے۔
    """
    api_key = key_manager.get_api_key()
    if not api_key:
        logger.warning("کوئی بھی Twelve Data API کلید دستیاب نہیں۔")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={timeframe}&outputsize={size}&apikey={api_key}"
    
    # --- اہم تبدیلی: API کال کو لاگ کریں ---
    logger.info(f"{symbol} کے لیے Twelve Data API سے ڈیٹا حاصل کیا جا رہا ہے...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        
        if response.status_code == 429: # Rate limit
            logger.warning(f"API کلید کی حد ختم ہو گئی۔ کلید کو گھمایا جا رہا ہے۔")
            key_manager.mark_key_as_limited(api_key)
            await asyncio.sleep(1)
            return await fetch_twelve_data_ohlc(symbol, timeframe, size)

        response.raise_for_status() # دیگر HTTP خرابیوں کے لیے
        
        data = response.json()
        
        # ڈیٹا کی توثیق
        validated_data = TwelveDataTimeSeries.model_validate(data)
        
        if validated_data.status == "ok" and validated_data.values:
            logger.info(f"{symbol} کے لیے کامیابی سے {len(validated_data.values)} کینڈلز حاصل کی گئیں۔")
            # Pydantic ماڈلز کو واپس ڈکشنری میں تبدیل کریں
            return [candle.model_dump() for candle in validated_data.values][::-1]
        else:
            logger.warning(f"{symbol} کے لیے ڈیٹا حاصل کرنے میں ناکامی: {validated_data.status}")
            return None
            
    except httpx.HTTPStatusError as e:
        logger.error(f"{symbol} کے لیے API کال میں خرابی: HTTP {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"{symbol} کے لیے نامعلوم خرابی: {e}", exc_info=True)
        return None

async def get_current_price_twelve_data(symbol: str, client: httpx.AsyncClient) -> Optional[float]:
    """کسی جوڑے کی موجودہ قیمت حاصل کرتا ہے۔"""
    api_key = key_manager.get_api_key()
    if not api_key:
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
        return float(data.get("price")) if data.get("price") else None
    except Exception:
        return None
            
