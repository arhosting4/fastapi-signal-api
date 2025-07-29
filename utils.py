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

MARKET_STATE_FILE = "market_state.json"

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
            logger.warning(f"اسکینر پول کی کلید {api_key[:8]}... کی حد ختم ہو گئی۔")
            key_manager.scanner_pool.mark_key_as_limited(api_key, daily_limit_exceeded=True)
            await asyncio.sleep(1)
            return await get_real_time_quotes(symbols)
        response.raise_for_status()
        data = response.json()
        quotes = {}
        if "symbol" in data and isinstance(data, dict):
            quotes[data["symbol"]] = data
        else:
            for symbol, details in data.items():
                if isinstance(details, dict):
                    quotes[symbol] = details
        return quotes
    except Exception as e:
        logger.error(f"کوٹس حاصل کرنے میں خرابی: {e}", exc_info=True)
        if api_key:
            key_manager.scanner_pool.mark_key_as_limited(api_key, daily_limit_exceeded=False)
        return None

async def fetch_twelve_data_ohlc(symbol: str) -> Optional[List[Candle]]:
    api_key = key_manager.analysis_pool.get_api_key()
    if not api_key:
        logger.warning(f"[{symbol}] OHLC کے لیے تجزیاتی پول میں کوئی API کلید دستیاب نہیں۔")
        return None
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={PRIMARY_TIMEFRAME}&outputsize={CANDLE_COUNT}&apikey={api_key}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        if response.status_code == 429:
            logger.warning(f"تجزیاتی پول کی کلید {api_key[:8]}... کی حد ختم ہو گئی۔")
            key_manager.analysis_pool.mark_key_as_limited(api_key, daily_limit_exceeded=True)
            await asyncio.sleep(1)
            return await fetch_twelve_data_ohlc(symbol)
        response.raise_for_status()
        data = response.json()
        if "values" not in data or data.get("status") != "ok":
            logger.warning(f"[{symbol}] کے لیے Twelve Data API نے خرابی واپس کی: {data.get('message', 'نامعلوم')}")
            return None
        validated_data = TwelveDataTimeSeries.model_validate(data)
        return validated_data.values[::-1]
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے OHLC ڈیٹا حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
        if api_key:
            key_manager.analysis_pool.mark_key_as_limited(api_key, daily_limit_exceeded=False)
        return None

async def get_current_prices_from_api(symbols: List[str]) -> Optional[Dict[str, float]]:
    if not symbols:
        return {}
    api_key = key_manager.monitoring_pool.get_api_key()
    if not api_key:
        logger.warning("قیمتیں حاصل کرنے کے لیے نگرانی پول میں کوئی API کلید دستیاب نہیں۔")
        return None
    symbol_str = ",".join(symbols)
    url = f"https://api.twelvedata.com/price?symbol={symbol_str}&apikey={api_key}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
        if response.status_code == 429:
            logger.warning(f"نگرانی پول کی کلید {api_key[:8]}... کی حد ختم ہو گئی۔")
            key_manager.monitoring_pool.mark_key_as_limited(api_key, daily_limit_exceeded=True)
            await asyncio.sleep(1)
            return await get_current_prices_from_api(symbols)
        response.raise_for_status()
        data = response.json()
        prices = {}
        if "price" in data and isinstance(data, dict):
             prices[symbols[0]] = float(data["price"])
        elif "price" in data:
             prices[symbols[0]] = float(data)
        else:
            for symbol, details in data.items():
                if isinstance(details, dict) and "price" in details:
                    prices[symbol] = float(details["price"])
        return prices
    except Exception as e:
        logger.error(f"API سے قیمتیں حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
        if api_key:
            key_manager.monitoring_pool.mark_key_as_limited(api_key, daily_limit_exceeded=False)
        return None

# ★★★ خرابی کو ٹھیک کرنے کے لیے یہ فنکشن واپس شامل کیا گیا ہے ★★★
def update_market_state(live_prices: Dict[str, float]):
    """مارکیٹ کی حالت کو اپ ڈیٹ کرتا ہے۔ (اب اس کا استعمال بہت محدود ہے)"""
    try:
        # یہ فنکشن اب زیادہ اہم نہیں، لیکن امپورٹ ایرر سے بچنے کے لیے موجود ہے۔
        # ہم اسے خالی بھی چھوڑ سکتے ہیں تاکہ یہ کچھ نہ کرے۔
        logger.info(f"Market state update called for {len(live_prices)} pairs. (Legacy function)")
        pass # فی الحال کچھ کرنے کی ضرورت نہیں
    except Exception as e:
        logger.error(f"مارکیٹ اسٹیٹ فائل لکھنے میں خرابی: {e}")
        
