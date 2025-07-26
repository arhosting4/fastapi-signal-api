# filename: utils.py

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

# ★★★ اہم تبدیلی: ویک اینڈ کے لیے کرپٹو جوڑے شامل کیے گئے ★★★

# ہفتے کے دنوں کے لیے جوڑے (فاریکس اور سونا)
AVAILABLE_PAIRS_WEEKDAY = ["XAU/USD", "EUR/USD", "GBP/USD"]

# ہفتے کے اختتام (ویک اینڈ) کے لیے جوڑے (کرپٹو)
AVAILABLE_PAIRS_WEEKEND = ["BTC/USD", "ETH/USD", "XRP/USD"]

CANDLE_COUNT = 100

def get_available_pairs() -> List[str]:
    """
    ہفتے کے دن کی بنیاد پر دستیاب تجارتی جوڑے واپس کرتا ہے۔
    """
    # datetime.utcnow().weekday() سوموار (0) سے اتوار (6) تک ایک نمبر واپس کرتا ہے
    # 0-4: سوموار سے جمعہ
    # 5-6: ہفتہ اور اتوار
    is_weekend = datetime.utcnow().weekday() >= 5 

    if is_weekend:
        logger.info(f"ویک اینڈ ہے، کرپٹو جوڑے استعمال کیے جا رہے ہیں: {AVAILABLE_PAIRS_WEEKEND}")
        return AVAILABLE_PAIRS_WEEKEND
    else:
        logger.info(f"ہفتے کا دن ہے، فاریکس جوڑے استعمال کیے جا رہے ہیں: {AVAILABLE_PAIRS_WEEKDAY}")
        return AVAILABLE_PAIRS_WEEKDAY

# --- باقی تمام فنکشنز ویسے ہی رہیں گے ---

async def fetch_twelve_data_ohlc(symbol: str, interval: str) -> Optional[List[Candle]]:
    api_key = key_manager.get_api_key()
    if not api_key:
        logger.warning(f"[{symbol}] کے لیے کوئی بھی Twelve Data API کلید دستیاب نہیں۔")
        return None
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={CANDLE_COUNT}&apikey={api_key}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        if response.status_code == 429:
            key_manager.mark_key_as_limited(api_key)
            await asyncio.sleep(1)
            return await fetch_twelve_data_ohlc(symbol, interval)
        response.raise_for_status()
        data = response.json()
        if "values" not in data or data.get("status") != "ok":
            return None
        validated_data = TwelveDataTimeSeries.model_validate(data)
        return validated_data.values[::-1]
    except Exception:
        return None

async def get_batch_prices_twelve_data(symbols: List[str], client: httpx.AsyncClient) -> Optional[Dict[str, float]]:
    if not symbols: return {}
    api_key = key_manager.get_api_key()
    if not api_key: return None
    
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
        prices = {}
        if len(symbols) == 1:
            if "price" in data: prices[symbols[0]] = float(data["price"])
        else:
            for symbol in symbols:
                if symbol in data and "price" in data[symbol]:
                    prices[symbol] = float(data[symbol]["price"])
        return prices
    except Exception:
        return None
        
