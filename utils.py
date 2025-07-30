# filename: utils.py

import os
import httpx
import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from key_manager import key_manager
from schemas import TwelveDataTimeSeries, Candle
from config import TRADING_PAIRS, API_CONFIG

logger = logging.getLogger(__name__)

PRIMARY_TIMEFRAME = API_CONFIG["PRIMARY_TIMEFRAME"]
CANDLE_COUNT = API_CONFIG["CANDLE_COUNT"]

def get_tradeable_pairs() -> List[str]:
    """تجارت کے قابل تمام جوڑوں کی فہرست واپس کرتا ہے۔"""
    today = datetime.utcnow().weekday()
    # ہفتے کے آخر میں صرف کرپٹو
    if today >= 5: 
        return TRADING_PAIRS["CRYPTO_PAIRS"]
    # ہفتے کے دنوں میں تمام جوڑے
    return TRADING_PAIRS["PRIMARY_PAIRS"] + TRADING_PAIRS["CRYPTO_PAIRS"]

async def _handle_rate_limit(response: httpx.Response, key: str):
    """429 ایرر کو ذہانت سے ہینڈل کرنے کے لیے ایک مددگار فنکشن"""
    try:
        data = response.json()
        message = data.get("message", "").lower()
        is_daily_limit = "for the day" in message
        key_manager.mark_key_as_limited(key, daily_limit_exceeded=is_daily_limit)
    except Exception as e:
        logger.error(f"ریٹ لمٹ ہینڈلر میں خرابی: {e}")
        key_manager.mark_key_as_limited(key, daily_limit_exceeded=False)
    await asyncio.sleep(2)

async def get_real_time_quotes(symbols: List[str]) -> Optional[Dict[str, Any]]:
    """کوٹس (جس میں قیمت اور پرسنٹیج تبدیلی شامل ہے) حاصل کرتا ہے اور انہیں صحیح طریقے سے پارس کرتا ہے۔"""
    if not symbols: 
        return {}
        
    api_key = key_manager.get_api_key()
    if not api_key: 
        logger.warning("کوٹس حاصل کرنے کے لیے کوئی API کلید دستیاب نہیں۔")
        return None
    
    # API کی حد کے اندر رہنے کے لیے بیچز میں تقسیم کریں
    batch_size = 7
    symbol_batches = [symbols[i:i + batch_size] for i in range(0, len(symbols), batch_size)]
    all_quotes = {}

    for batch in symbol_batches:
        symbol_str = ",".join(batch)
        url = f"https://api.twelvedata.com/quote?symbol={symbol_str}&apikey={api_key}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=15)
            
            if response.status_code == 429:
                await _handle_rate_limit(response, api_key)
                # اگر ایک کلید محدود ہو جائے تو اگلی کلید کے ساتھ دوبارہ کوشش کریں
                return await get_real_time_quotes(symbols) 

            response.raise_for_status()
            data = response.json()
            
            quotes_batch = {}
            if "symbol" in data and isinstance(data, dict):
                quotes_batch[data["symbol"]] = data
            elif isinstance(data, list): # کچھ اینڈپوائنٹس فہرست واپس کرتے ہیں
                 for item in data:
                    if isinstance(item, dict) and "symbol" in item:
                        quotes_batch[item["symbol"]] = item
            elif isinstance(data, dict):
                for symbol, details in data.items():
                    if isinstance(details, dict) and "symbol" in details:
                        quotes_batch[details["symbol"]] = details
            
            if not quotes_batch:
                logger.warning(f"کوٹس API سے کوئی درست ڈیٹا پارس نہیں کیا جا سکا۔ جواب: {data}")
            
            all_quotes.update(quotes_batch)

        except Exception as e:
            logger.error(f"کوٹس حاصل کرنے میں خرابی: {e}", exc_info=True)
            key_manager.mark_key_as_limited(api_key, daily_limit_exceeded=False)
            return None # ایک خرابی کی صورت میں، پورا عمل روک دیں
        
        # ہر بیچ کے درمیان تھوڑا وقفہ دیں
        await asyncio.sleep(1)

    return all_quotes

async def fetch_twelve_data_ohlc(symbol: str) -> Optional[List[Candle]]:
    """ایک جوڑے کے لیے OHLC کینڈلز لاتا ہے۔"""
    api_key = key_manager.get_api_key()
    if not api_key: 
        logger.warning(f"[{symbol}] OHLC کے لیے کوئی API کلید دستیاب نہیں۔")
        return None
        
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={PRIMARY_TIMEFRAME}&outputsize={CANDLE_COUNT}&apikey={api_key}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        if response.status_code == 429:
            await _handle_rate_limit(response, api_key)
            return await fetch_twelve_data_ohlc(symbol)
        response.raise_for_status()
        data = response.json()
        if "values" not in data or data.get("status") != "ok": 
            logger.warning(f"[{symbol}] کے لیے Twelve Data API نے خرابی واپس کی: {data.get('message', 'نامعلوم')}")
            return None
        return TwelveDataTimeSeries.model_validate(data).values[::-1]
    except Exception as e:
        logger.error(f"[{symbol}] OHLC ڈیٹا حاصل کرنے میں خرابی: {e}", exc_info=True)
        key_manager.mark_key_as_limited(api_key, daily_limit_exceeded=False)
        return None
                    
