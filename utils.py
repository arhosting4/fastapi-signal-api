# filename: utils.py

import os
import httpx
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from key_manager import key_manager
from schemas import TwelveDataTimeSeries, Candle
from config import API_CONFIG

logger = logging.getLogger(__name__)

# --- کنفیگریشن سے متغیرات ---
PRIMARY_TIMEFRAME = API_CONFIG["PRIMARY_TIMEFRAME"]
CANDLE_COUNT = API_CONFIG["CANDLE_COUNT"]

# ★★★ مکمل طور پر اپ ڈیٹ شدہ اور مضبوط فنکشن ★★★
async def get_real_time_quotes(symbols: List[str]) -> Optional[Dict[str, Any]]:
    """
    دی گئی علامتوں کی فہرست کے لیے TwelveData API سے تازہ ترین کوٹس حاصل کرتا ہے۔
    یہ فنکشن اب 'گارڈین' کیز استعمال کرتا ہے اور جواب کی باڈی کی توثیق کرتا ہے۔
    """
    if not symbols:
        return {}

    # ★★★ تبدیلی: گارڈین پول سے ایک کی حاصل کریں ★★★
    api_key = key_manager.get_guardian_key()
    if not api_key:
        logger.warning("🛡️ نگرانی (کوٹس) کے لیے کوئی API کلید دستیاب نہیں۔")
        return None

    symbol_str = ",".join(symbols)
    url = f"https://api.twelvedata.com/quote?symbol={symbol_str}&apikey={api_key}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=20)

        if response.status_code == 429:
            # اگر کی کی حد ختم ہو گئی ہے تو اسے رپورٹ کریں
            data = response.json()
            is_daily = "day" in data.get("message", "").lower()
            key_manager.report_key_issue(api_key, is_daily_limit=is_daily)
            return None

        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and data.get("status") == "error":
            logger.warning(f"کوٹس API نے خرابی واپس کی: {data.get('message', 'نامعلوم خرابی')}")
            return None

        quotes = {}
        if isinstance(data, list):
            # کچھ علامتوں کے لیے جواب ایک فہرست ہو سکتا ہے
            for item in data:
                if isinstance(item, dict) and "symbol" in item:
                    quotes[item["symbol"]] = item
        elif isinstance(data, dict):
            # ایک علامت یا کئی علامتوں کے لیے جواب ایک ڈکشنری ہو سکتا ہے
            if "symbol" in data:
                quotes[data["symbol"]] = data
            else:
                for symbol, details in data.items():
                    if isinstance(details, dict) and details.get("status") != "error":
                        quotes[symbol] = details
                    elif isinstance(details, dict):
                        logger.warning(f"علامت '{symbol}' کے لیے کوٹ حاصل کرنے میں خرابی: {details.get('message')}")

        if not quotes:
            logger.warning(f"کوٹس API سے کوئی درست ڈیٹا پارس نہیں کیا جا سکا۔ جواب: {data}")
            return None
            
        return quotes

    except httpx.HTTPStatusError as e:
        logger.error(f"کوٹس حاصل کرنے میں HTTP خرابی: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"کوٹس حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
        return None

# ★★★ مکمل طور پر اپ ڈیٹ شدہ اور مضبوط فنکشن ★★★
async def fetch_twelve_data_ohlc(symbol: str) -> Optional[List[Candle]]:
    """
    TwelveData API سے OHLC کینڈلز لاتا ہے۔
    یہ فنکشن اب 'ہنٹر' کیز استعمال کرتا ہے اور جواب کی باڈی کی توثیق کرتا ہے۔
    """
    # ★★★ تبدیلی: ہنٹر پول سے ایک کی حاصل کریں ★★★
    api_key = key_manager.get_hunter_key()
    if not api_key:
        logger.warning(f"🏹 [{symbol}] OHLC کے لیے کوئی API کلید دستیاب نہیں۔")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={PRIMARY_TIMEFRAME}&outputsize={CANDLE_COUNT}&apikey={api_key}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=20)
        
        if response.status_code == 429:
            # اگر کی کی حد ختم ہو گئی ہے تو اسے رپورٹ کریں
            data = response.json()
            is_daily = "day" in data.get("message", "").lower()
            key_manager.report_key_issue(api_key, is_daily_limit=is_daily)
            return None

        response.raise_for_status()
        data = response.json()
        
        if "status" not in data or data.get("status") != "ok":
            logger.warning(f"[{symbol}] کے لیے Twelve Data API نے خرابی واپس کی: {data.get('message', 'نامعلوم خرابی')}")
            return None

        # Pydantic ماڈل کا استعمال کرکے جواب کی توثیق کریں
        validated_data = TwelveDataTimeSeries.model_validate(data)
        # API سے ڈیٹا الٹا آتا ہے، اسے سیدھا کریں
        return validated_data.values[::-1]

    except httpx.HTTPStatusError as e:
        logger.error(f"[{symbol}] کے لیے OHLC ڈیٹا حاصل کرنے میں HTTP خرابی: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے OHLC ڈیٹا حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
        return None
        
