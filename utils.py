# filename: utils.py

import os
import httpx
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from key_manager import key_manager
from schemas import TwelveDataTimeSeries, Candle

logger = logging.getLogger(__name__)

# کنفیگریشن
AVAILABLE_PAIRS_WEEKDAY = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
AVAILABLE_PAIRS_WEEKEND = ["BTC/USD"]
CANDLE_COUNT = 100
PRIMARY_TIMEFRAME = "15min"

def get_available_pairs() -> List[str]:
    """ہفتے کے دن کی بنیاد پر دستیاب جوڑے واپس کرتا ہے۔"""
    today = datetime.utcnow().weekday()
    if today >= 5: 
        return AVAILABLE_PAIRS_WEEKEND
    return AVAILABLE_PAIRS_WEEKDAY

async def fetch_twelve_data_ohlc(symbol: str) -> Optional[List[Candle]]:
    """TwelveData API سے OHLC کینڈلز لاتا ہے۔"""
    api_key = key_manager.get_api_key()
    if not api_key:
        logger.warning(f"[{symbol}] OHLC کے لیے کوئی API کلید دستیاب نہیں۔")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={PRIMARY_TIMEFRAME}&outputsize={CANDLE_COUNT}&apikey={api_key}"
    logger.info(f"[{symbol}] کے لیے Twelve Data API سے ڈیٹا حاصل کیا جا رہا ہے (کلید: {api_key[:8]}...)")
    
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
            logger.warning(f"[{symbol}] کے لیے Twelve Data API نے خرابی واپس کی: {data.get('message', 'نامعلوم')}")
            return None

        validated_data = TwelveDataTimeSeries.model_validate(data)
        logger.info(f"[{symbol}] کے لیے کامیابی سے {len(validated_data.values)} کینڈلز حاصل کی گئیں۔")
        return validated_data.values[::-1]
            
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے OHLC ڈیٹا حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
        return None

# ==============================================================================
# ★★★ بنیادی غلطی کا ازالہ: یہ فنکشن غائب تھا ★★★
# ==============================================================================
async def get_current_prices_from_api(symbols: List[str]) -> Optional[Dict[str, float]]:
    """
    دی گئی علامتوں کی فہرست کے لیے TwelveData API سے تازہ ترین قیمتیں حاصل کرتا ہے۔
    """
    if not symbols:
        return {}

    api_key = key_manager.get_api_key()
    if not api_key:
        logger.warning("قیمتیں حاصل کرنے کے لیے کوئی API کلید دستیاب نہیں۔")
        return None

    # علامتوں کو کوما سے الگ کی گئی سٹرنگ میں تبدیل کریں
    symbol_str = ",".join(symbols)
    url = f"https://api.twelvedata.com/price?symbol={symbol_str}&apikey={api_key}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)

        if response.status_code == 429:
            logger.warning(f"API کلید کی حد ختم ہو گئی۔ کلید کو گھمایا جا رہا ہے۔")
            key_manager.mark_key_as_limited(api_key)
            await asyncio.sleep(1)
            return await get_current_prices_from_api(symbols)

        response.raise_for_status()
        data = response.json()

        # جواب کی ساخت کو ہینڈل کریں (ایک علامت یا متعدد)
        prices = {}
        if "price" in data and isinstance(data['price'], (int, float, str)): # اگر صرف ایک علامت کی درخواست کی گئی ہو
            prices[symbols[0]] = float(data["price"])
        else: # اگر متعدد علامتوں کی درخواست کی گئی ہو
            for symbol, details in data.items():
                if isinstance(details, dict) and "price" in details:
                    prices[symbol] = float(details["price"])
        
        if prices:
            logger.info(f"کامیابی سے {len(prices)} قیمتیں حاصل اور پارس کی گئیں۔")
            return prices
        else:
            logger.warning(f"API سے قیمتیں حاصل ہوئیں لیکن پارس نہیں کی جا سکیں: {data}")
            return None

    except Exception as e:
        logger.error(f"API سے قیمتیں حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
        return None
    
