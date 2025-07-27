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

# کنفیگریشن پیرامیٹرز
AVAILABLE_PAIRS_WEEKDAY = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
AVAILABLE_PAIRS_WEEKEND = ["BTC/USD"]
CANDLE_COUNT = 100
PRIMARY_TIMEFRAME = "15min"

def get_available_pairs() -> List[str]:
    """ہفتے کے دن کی بنیاد پر دستیاب جوڑے واپس کرتا ہے۔"""
    today = datetime.utcnow().weekday()
    return AVAILABLE_PAIRS_WEEKEND if today >= 5 else AVAILABLE_PAIRS_WEEKDAY

async def fetch_twelve_data_ohlc(symbol: str) -> Optional[List[Candle]]:
    """
    TwelveData API سے OHLC کینڈلز لاتا ہے۔
    """
    api_key = key_manager.get_api_key()
    if not api_key:
        logger.warning(f"[{symbol}] کے لیے کوئی بھی Twelve Data API کلید دستیاب نہیں۔")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={PRIMARY_TIMEFRAME}&outputsize={CANDLE_COUNT}&apikey={api_key}"
    logger.info(f"[{symbol}] کے لیے Twelve Data API سے ڈیٹا حاصل کیا جا رہا ہے (کلید: {api_key[:8]}...)")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        
        if response.status_code == 429:
            response_data = response.json()
            message = response_data.get("message", "").lower()
            duration = 65
            if "daily limit" in message:
                duration = 24 * 60 * 60
                logger.critical(f"API کلید {api_key[:8]}... اپنی یومیہ حد تک پہنچ گئی ہے!")
            
            logger.warning(f"API کلید {api_key[:8]}... کی حد ختم ہو گئی۔ اسے {duration} سیکنڈ کے لیے محدود کیا جا رہا ہے۔")
            key_manager.mark_key_as_limited(api_key, duration_seconds=duration)
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
        return validated_data.values[::-1]
            
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے نامعلوم خرابی: {e}", exc_info=True)
        return None

# ★★★ یہاں غلطی کو درست کیا گیا ہے ★★★
async def get_multiple_prices_twelve_data(symbols: List[str]) -> Dict[str, float]:
    """
    ایک ہی API کال میں متعدد جوڑوں کی قیمتیں حاصل کرتا ہے۔
    یہ فنکشن اب Twelve Data کے مختلف جوابات کو ہینڈل کرنے کے قابل ہے۔
    """
    if not symbols:
        return {}

    api_key = key_manager.get_api_key()
    if not api_key:
        logger.warning("قیمتیں حاصل کرنے کے لیے کوئی API کلید دستیاب نہیں۔")
        return {}

    symbol_str = ",".join(symbols)
    url = f"https://api.twelvedata.com/price?symbol={symbol_str}&apikey={api_key}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)

        if response.status_code == 429:
            response_data = response.json()
            message = response_data.get("message", "").lower()
            duration = 65
            if "daily limit" in message: duration = 24 * 60 * 60
            key_manager.mark_key_as_limited(api_key, duration_seconds=duration)
            await asyncio.sleep(1)
            return await get_multiple_prices_twelve_data(symbols)

        response.raise_for_status()
        data = response.json()

        prices = {}
        # اگر جواب ایک واحد آبجیکٹ ہے (ایک علامت کے لیے)
        if isinstance(data, dict) and 'symbol' in data and 'price' in data:
            prices[data['symbol']] = float(data['price'])
        # اگر جواب آبجیکٹس کی فہرست ہے (متعدد علامتوں کے لیے)
        elif isinstance(data, list):
            for item in data:
                if 'symbol' in item and 'price' in item:
                    prices[item['symbol']] = float(item['price'])
        # اگر جواب میں ہر علامت کے لیے ایک کلید ہے
        elif isinstance(data, dict):
             for symbol, details in data.items():
                 if isinstance(details, dict) and 'price' in details:
                     prices[symbol] = float(details['price'])

        if not prices:
            logger.warning(f"API سے قیمتیں حاصل ہوئیں لیکن پارس نہیں کی جا سکیں: {data}")

        return prices

    except Exception as e:
        logger.error(f"متعدد قیمتیں حاصل کرنے میں خرابی: {e}", exc_info=True)
        return {}
            
