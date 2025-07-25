# filename: utils.py

# ... (باقی تمام امپورٹس اور فنکشنز ویسے ہی رہیں گے) ...
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

AVAILABLE_PAIRS_WEEKDAY = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
AVAILABLE_PAIRS_WEEKEND = ["BTC/USD"]
CANDLE_COUNT = 100

def get_available_pairs() -> List[str]:
    today = datetime.utcnow().weekday()
    return AVAILABLE_PAIRS_WEEKEND if today >= 5 else AVAILABLE_PAIRS_WEEKDAY

async def fetch_twelve_data_ohlc(symbol: str, interval: str) -> Optional[List[Candle]]:
    # ... (یہ فنکشن بالکل ٹھیک ہے اور ویسے ہی رہے گا) ...
    api_key = key_manager.get_api_key()
    if not api_key:
        logger.warning(f"[{symbol}] کے لیے کوئی بھی Twelve Data API کلید دستیاب نہیں۔")
        return None
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={CANDLE_COUNT}&apikey={api_key}"
    logger.info(f"[{symbol}] کے لیے [{interval}] ٹائم فریم پر Twelve Data API سے ڈیٹا حاصل کیا جا رہا ہے...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        if response.status_code == 429:
            logger.warning(f"API کلید کی حد ختم ہو گئی۔ کلید کو گھمایا جا رہا ہے۔")
            key_manager.mark_key_as_limited(api_key)
            await asyncio.sleep(1)
            return await fetch_twelve_data_ohlc(symbol, interval)
        response.raise_for_status()
        data = response.json()
        if "values" not in data or data.get("status") != "ok":
            logger.warning(f"[{symbol}] کے لیے Twelve Data API نے خرابی واپس کی: {data.get('message', 'کوئی خرابی کا پیغام نہیں')}")
            return None
        validated_data = TwelveDataTimeSeries.model_validate(data)
        logger.info(f"[{symbol}] کے لیے کامیابی سے {len(validated_data.values)} کینڈلز حاصل کی گئیں۔")
        return validated_data.values[::-1]
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے نامعلوم خرابی: {e}", exc_info=True)
        return None

# ★★★ اہم اور حتمی تبدیلی ★★★
async def get_batch_prices_twelve_data(symbols: List[str], client: httpx.AsyncClient) -> Optional[Dict[str, float]]:
    """
    ایک ہی API کال میں متعدد جوڑوں کی موجودہ قیمتیں حاصل کرتا ہے۔
    """
    if not symbols:
        return {}
        
    api_key = key_manager.get_api_key()
    if not api_key:
        return None
        
    # تمام سمبلز کو کوما سے الگ کرکے ایک اسٹرنگ بنائیں
    symbol_str = ",".join(symbols)
    url = f"https://api.twelvedata.com/price?symbol={symbol_str}&apikey={api_key}"
    
    try:
        response = await client.get(url, timeout=10)
        if response.status_code == 429:
            key_manager.mark_key_as_limited(api_key)
            await asyncio.sleep(1)
            return await get_batch_prices_twelve_data(symbols, client)
            
        response.raise_for_status()
        data = response.json()

        # جواب کو ایک ڈکشنری میں تبدیل کریں: {'EUR/USD': 1.12, 'BTC/USD': 29000.0}
        prices = {}
        if len(symbols) == 1: # اگر صرف ایک سمبل ہے
            if "price" in data:
                prices[symbols[0]] = float(data["price"])
        else: # اگر متعدد سمبلز ہیں
            for symbol in symbols:
                if symbol in data and "price" in data[symbol]:
                    prices[symbol] = float(data[symbol]["price"])
        return prices
        
    except Exception as e:
        logger.error(f"بیچ قیمتیں حاصل کرنے میں خرابی: {e}")
        return None
        
