# filename: utils.py

import os
import httpx
import asyncio
import logging
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from key_manager import key_manager
from schemas import TwelveDataTimeSeries, Candle
from config import TRADING_PAIRS, API_CONFIG

logger = logging.getLogger(__name__)

PRIMARY_TIMEFRAME = API_CONFIG["PRIMARY_TIMEFRAME"]
CANDLE_COUNT = API_CONFIG["CANDLE_COUNT"]

def get_tradeable_pairs() -> List[str]:
    today = datetime.utcnow().weekday()
    if today >= 5:
        return TRADING_PAIRS["CRYPTO_PAIRS"]
    return TRADING_PAIRS["PRIMARY_PAIRS"] + TRADING_PAIRS["CRYPTO_PAIRS"]

async def get_real_time_quotes(symbols: List[str]) -> Optional[Dict[str, Any]]:
    if not symbols:
        return {}
    api_key = key_manager.scanner_pool.get_api_key()
    if not api_key:
        logger.warning("کوٹس حاصل کرنے کے لیے اسکینر پول میں کوئی API کلید دستیاب نہیں۔")
        return None
    symbol_str = ",".join(symbols)
    url = f"https://api.twelvedata.com/quote?symbol={symbol_str}&apikey={api_key}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        if response.status_code == 429:
            key_manager.scanner_pool.mark_key_as_limited(api_key, daily_limit_exceeded=True)
            return await get_real_time_quotes(symbols)
        response.raise_for_status()
        data = response.json()
        
        # ★★★ نیا، مضبوط پارسنگ کا طریقہ ★★★
        quotes = {}
        # اگر جواب ایک فہرست ہے (متعدد غلط علامتوں کے لیے)
        if isinstance(data, list):
            logger.warning(f"API نے کوٹس کے لیے ایک فہرست واپس کی، ممکنہ طور پر غلط علامتیں: {data}")
            return {} # خالی ڈکشنری واپس کریں
            
        # اگر جواب ایک واحد آبجیکٹ ہے
        if "symbol" in data and isinstance(data, dict):
            quotes[data["symbol"]] = data
        # اگر جواب علامتوں کی ڈکشنری ہے
        else:
            for item in data.values():
                if isinstance(item, dict) and "symbol" in item:
                    quotes[item["symbol"]] = item
        
        if not quotes:
            logger.warning(f"کوٹس API سے کوئی درست ڈیٹا پارس نہیں کیا جا سکا۔ جواب: {data}")

        return quotes
    except Exception as e:
        logger.error(f"کوٹس حاصل کرنے میں خرابی: {e}", exc_info=True)
        if api_key:
            key_manager.scanner_pool.mark_key_as_limited(api_key, daily_limit_exceeded=False)
        return None

async def fetch_twelve_data_ohlc(symbol: str) -> Optional[List[Candle]]:
    api_key = key_manager.analysis_pool.get_api_key()
    if not api_key:
        return None
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={PRIMARY_TIMEFRAME}&outputsize={CANDLE_COUNT}&apikey={api_key}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        if response.status_code == 429:
            key_manager.analysis_pool.mark_key_as_limited(api_key, daily_limit_exceeded=True)
            return await fetch_twelve_data_ohlc(symbol)
        response.raise_for_status()
        data = response.json()
        if "values" not in data or data.get("status") != "ok":
            return None
        validated_data = TwelveDataTimeSeries.model_validate(data)
        return validated_data.values[::-1]
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے OHLC ڈیٹا حاصل کرنے میں خرابی: {e}", exc_info=True)
        if api_key:
            key_manager.analysis_pool.mark_key_as_limited(api_key, daily_limit_exceeded=False)
        return None

async def get_current_prices_from_api(symbols: List[str]) -> Optional[Dict[str, float]]:
    if not symbols:
        return {}
    api_key = key_manager.monitoring_pool.get_api_key()
    if not api_key:
        return None
    symbol_str = ",".join(symbols)
    url = f"https://api.twelvedata.com/price?symbol={symbol_str}&apikey={api_key}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
        if response.status_code == 429:
            key_manager.monitoring_pool.mark_key_as_limited(api_key, daily_limit_exceeded=True)
            return await get_current_prices_from_api(symbols)
        response.raise_for_status()
        data = response.json()

        # ★★★ نیا، مضبوط پارسنگ کا طریقہ ★★★
        prices = {}
        # اگر جواب ایک واحد قیمت ہے
        if "price" in data and isinstance(data, dict):
             prices[symbols[0]] = float(data["price"])
        # اگر جواب علامتوں کی ڈکشنری ہے
        else:
            for symbol, details in data.items():
                if isinstance(details, dict) and "price" in details:
                    prices[symbol] = float(details["price"])
        
        if not prices:
            logger.warning(f"قیمت API سے کوئی درست ڈیٹا پارس نہیں کیا جا سکا۔ جواب: {data}")

        return prices
    except Exception as e:
        logger.error(f"API سے قیمتیں حاصل کرنے میں خرابی: {e}", exc_info=True)
        if api_key:
            key_manager.monitoring_pool.mark_key_as_limited(api_key, daily_limit_exceeded=False)
        return None

def update_market_state(live_prices: Dict[str, float]):
    try:
        logger.info(f"Market state update called for {len(live_prices)} pairs. (Legacy function)")
        pass
    except Exception as e:
        logger.error(f"مارکیٹ اسٹیٹ فائل لکھنے میں خرابی: {e}")
    
