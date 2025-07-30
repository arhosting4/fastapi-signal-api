# filename: utils.py

import os
import httpx
import asyncio
import logging
import json
from datetime import datetime # ★★★ خرابی کو ٹھیک کرنے کے لیے یہ لائن واپس شامل کی گئی ہے ★★★
from typing import List, Optional, Dict, Any

from key_manager import key_manager
from schemas import TwelveDataTimeSeries, Candle
from config import TRADING_PAIRS, API_CONFIG

logger = logging.getLogger(__name__)

PRIMARY_TIMEFRAME = API_CONFIG["PRIMARY_TIMEFRAME"]
CANDLE_COUNT = API_CONFIG["CANDLE_COUNT"]

def get_tradeable_pairs() -> List[str]:
    # اب 'datetime' یہاں پر کام کرے گا
    today = datetime.utcnow().weekday()
    if today >= 5: return TRADING_PAIRS["CRYPTO_PAIRS"]
    return TRADING_PAIRS["PRIMARY_PAIRS"] + TRADING_PAIRS["CRYPTO_PAIRS"]

async def _handle_rate_limit(response: httpx.Response, key: str):
    """429 ایرر کو ذہانت سے ہینڈل کرنے کے لیے ایک مددگار فنکشن"""
    try:
        data = response.json()
        message = data.get("message", "").lower()
        is_daily_limit = "for the day" in message
        logger.warning(f"کلید {key[:8]}... کی حد ختم۔ روزانہ کی حد: {is_daily_limit}")
        key_manager.mark_key_as_limited(key, daily_limit_exceeded=is_daily_limit)
    except Exception as e:
        logger.error(f"ریٹ لمٹ ہینڈلر میں خرابی: {e}")
        key_manager.mark_key_as_limited(key, daily_limit_exceeded=False)
    await asyncio.sleep(2)

async def get_real_time_quotes(symbols: List[str]) -> Optional[Dict[str, Any]]:
    if not symbols: return {}
    api_key = key_manager.get_api_key()
    if not api_key: return None
    
    url = f"https://api.twelvedata.com/quote?symbol={','.join(symbols)}&apikey={api_key}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        if response.status_code == 429:
            await _handle_rate_limit(response, api_key)
            return await get_real_time_quotes(symbols)
        response.raise_for_status()
        data = response.json()
        quotes = {}
        if isinstance(data, list): return {}
        if "symbol" in data and isinstance(data, dict): quotes[data["symbol"]] = data
        else:
            for item in data.values():
                if isinstance(item, dict) and "symbol" in item:
                    quotes[item["symbol"]] = item
        return quotes
    except Exception as e:
        logger.error(f"کوٹس حاصل کرنے میں خرابی: {e}", exc_info=True)
        if api_key: key_manager.mark_key_as_limited(api_key, daily_limit_exceeded=False)
        return None

async def fetch_twelve_data_ohlc(symbol: str) -> Optional[List[Candle]]:
    api_key = key_manager.get_api_key()
    if not api_key: return None
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={PRIMARY_TIMEFRAME}&outputsize={CANDLE_COUNT}&apikey={api_key}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        if response.status_code == 429:
            await _handle_rate_limit(response, api_key)
            return await fetch_twelve_data_ohlc(symbol)
        response.raise_for_status()
        data = response.json()
        if "values" not in data or data.get("status") != "ok": return None
        return TwelveDataTimeSeries.model_validate(data).values[::-1]
    except Exception as e:
        logger.error(f"[{symbol}] OHLC ڈیٹا حاصل کرنے میں خرابی: {e}", exc_info=True)
        if api_key: key_manager.mark_key_as_limited(api_key, daily_limit_exceeded=False)
        return None

async def get_current_prices_from_api(symbols: List[str]) -> Optional[Dict[str, float]]:
    if not symbols: return {}
    api_key = key_manager.get_api_key()
    if not api_key: return None
    url = f"https://api.twelvedata.com/price?symbol={','.join(symbols)}&apikey={api_key}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
        if response.status_code == 429:
            await _handle_rate_limit(response, api_key)
            return await get_current_prices_from_api(symbols)
        response.raise_for_status()
        data = response.json()
        prices = {}
        if "price" in data and isinstance(data, dict): prices[symbols[0]] = float(data["price"])
        elif "price" in data: prices[symbols[0]] = float(data)
        else:
            for symbol, details in data.items():
                if isinstance(details, dict) and "price" in details:
                    prices[symbol] = float(details["price"])
        return prices
    except Exception as e:
        logger.error(f"API سے قیمتیں حاصل کرنے میں خرابی: {e}", exc_info=True)
        if api_key: key_manager.mark_key_as_limited(api_key, daily_limit_exceeded=False)
        return None

def update_market_state(live_prices: Dict[str, float]):
    pass
        
