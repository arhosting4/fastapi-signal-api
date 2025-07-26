import os
import httpx
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict

from key_manager import KeyManager
from schemas import TwelveDataTimeSeries, Candle

logger = logging.getLogger(__name__)
key_manager = KeyManager()

# ==============================================================================
# کنفیگریشن پیرامیٹرز براہ راست یہاں شامل کر دیے گئے ہیں
# ==============================================================================
AVAILABLE_PAIRS_WEEKDAY = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
AVAILABLE_PAIRS_WEEKEND = ["BTC/USD"]
CANDLE_COUNT = 100
PRIMARY_TIMEFRAME = "15min"
# ==============================================================================

def get_available_pairs() -> List[str]:
    """ہفتے کے دن کی بنیاد پر دستیاب جوڑے واپس کرتا ہے۔"""
    today = datetime.utcnow().weekday()
    # 0-4 سوموار سے جمعہ، 5-6 ہفتہ-اتوار
    if today >= 5: 
        return AVAILABLE_PAIRS_WEEKEND
    return AVAILABLE_PAIRS_WEEKDAY

async def fetch_twelve_data_ohlc(symbol: str) -> Optional[List[Candle]]:
    """
    TwelveData API سے OHLC کینڈلز لاتا ہے اور انہیں Pydantic ماڈلز کی فہرست کے طور پر واپس کرتا ہے۔
    """
    api_key = key_manager.get_api_key()
    if not api_key:
        logger.warning("کوئی بھی Twelve Data API کلید دستیاب نہیں۔")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={PRIMARY_TIMEFRAME}&outputsize={CANDLE_COUNT}&apikey={api_key}"
    logger.info(f"[{symbol}] کے لیے Twelve Data API سے ڈیٹا حاصل کیا جا رہا ہے...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        
        if response.status_code == 429:
            logger.warning(f"API کلید کی حد ختم ہو گئی۔ کلید کو گھمایا جا رہا ہے۔")
            key_manager.mark_key_as_limited(api_key)
            await asyncio.sleep(1)
            return await fetch_twelve_data_ohlc(symbol)

        response.raise_for_status()
        data = response.json()
        
        if "values" not in data or data.get("status") != "ok":
            error_message = data.get("message", "کوئی خرابی کا پیغام نہیں")
            logger.warning(f"[{symbol}] کے لیے Twelve Data API نے خرابی واپس کی: {error_message}")
            return None

        validated_data = TwelveDataTimeSeries.model_validate(data)
        
        logger.info(f"[{symbol}] کے لیے کامیابی سے {len(validated_data.values)} کینڈلز حاصل کی گئیں۔")
        
        # API سے ڈیٹا تازہ ترین سے پرانے کی طرف آتا ہے، اسے الٹا کریں
        return validated_data.values[::-1]
            
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے نامعلوم خرابی: {e}", exc_info=True)
        return None

async def get_current_price_twelve_data(symbol: str, client: httpx.AsyncClient) -> Optional[float]:
    """
    کسی جوڑے کی موجودہ قیمت حاصل کرتا ہے۔
    """
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
    except Exception as e:
        logger.error(f"موجودہ قیمت حاصل کرنے میں خرابی: {e}")
        return None
        
