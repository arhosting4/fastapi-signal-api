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

# --- کنفیگریشن سے متغیرات ---
# ★★★ یہاں غلطی تھی، اسے ٹھیک کر دیا گیا ہے ★★★
PAIRS_TO_MONITOR = TRADING_PAIRS["PAIRS_TO_MONITOR"]
PRIMARY_TIMEFRAME = API_CONFIG["PRIMARY_TIMEFRAME"]
CANDLE_COUNT = API_CONFIG["CANDLE_COUNT"]

def get_pairs_to_monitor() -> List[str]:
    """
    کنفیگریشن سے نگرانی کے قابل جوڑوں کی فہرست واپس کرتا ہے۔
    """
    return PAIRS_TO_MONITOR

async def get_real_time_quotes(symbols: List[str]) -> Optional[Dict[str, Any]]:
    """
    دی گئی علامتوں کی فہرست کے لیے TwelveData API سے تازہ ترین کوٹس حاصل کرتا ہے۔
    یہ فنکشن اب 'گارڈین' کیز استعمال کرتا ہے۔
    """
    if not symbols:
        return {}

    api_key = key_manager.get_guardian_key()
    if not api_key:
        logger.warning("نگرانی کے لیے کوئی API کلید دستیاب نہیں۔")
        return None

    symbol_str = ",".join(symbols)
    url = f"https://api.twelvedata.com/quote?symbol={symbol_str}&apikey={api_key}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=20)

        if response.status_code == 429:
            data = response.json()
            is_daily = "day" in data.get("message", "").lower()
            key_manager.report_key_issue(api_key, is_daily_limit=is_daily)
            return None

        response.raise_for_status()
        data = response.json()

        quotes = {}
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "symbol" in item:
                    quotes[item["symbol"]] = item
        elif isinstance(data, dict):
            if "symbol" in data:
                quotes[data["symbol"]] = data
            else:
                for symbol, details in data.items():
                    if isinstance(details, dict):
                        quotes[symbol] = details

        if not quotes:
            logger.warning(f"کوٹس API سے کوئی درست ڈیٹا پارس نہیں کیا جا سکا۔ جواب: {data}")
            return None
            
        return quotes

    except Exception as e:
        logger.error(f"کوٹس حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
        return None

async def fetch_twelve_data_ohlc(symbol: str) -> Optional[List[Candle]]:
    """
    TwelveData API سے OHLC کینڈلز لاتا ہے۔
    یہ فنکشن اب 'ہنٹر' کیز استعمال کرتا ہے۔
    """
    api_key = key_manager.get_hunter_key()
    if not api_key:
        logger.warning(f"[{symbol}] OHLC کے لیے کوئی API کلید دستیاب نہیں۔")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={PRIMARY_TIMEFRAME}&outputsize={CANDLE_COUNT}&apikey={api_key}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=20)
        
        if response.status_code == 429:
            data = response.json()
            is_daily = "day" in data.get("message", "").lower()
            key_manager.report_key_issue(api_key, is_daily_limit=is_daily)
            return None

        response.raise_for_status()
        data = response.json()
        
        if "values" not in data or data.get("status") != "ok":
            logger.warning(f"[{symbol}] کے لیے Twelve Data API نے خرابی واپس کی: {data.get('message', 'نامعلوم')}")
            return None

        validated_data = TwelveDataTimeSeries.model_validate(data)
        return validated_data.values[::-1]
            
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے OHLC ڈیٹا حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
        return None
        
