# filename: utils.py

import os
import httpx
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict

from key_manager import key_manager # اپ ڈیٹ شدہ key_manager امپورٹ کریں
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
    TwelveData API سے OHLC کینڈلز لاتا ہے اور انہیں Pydantic ماڈلز کی فہرست کے طور پر واپس کرتا ہے۔
    ★★★ اب یہ ذہین کی مینیجر کا استعمال کرتا ہے۔ ★★★
    """
    api_key = key_manager.get_api_key()
    if not api_key:
        logger.warning(f"[{symbol}] کے لیے کوئی بھی Twelve Data API کلید دستیاب نہیں۔ ڈیٹا حاصل نہیں کیا جا سکتا۔")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={PRIMARY_TIMEFRAME}&outputsize={CANDLE_COUNT}&apikey={api_key}"
    logger.info(f"[{symbol}] کے لیے Twelve Data API سے ڈیٹا حاصل کیا جا رہا ہے (کلید: {api_key[:8]}...)")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        
        if response.status_code == 429:
            # ★★★ ذہین پابندی کی منطق ★★★
            response_data = response.json()
            message = response_data.get("message", "").lower()
            
            duration = 65  # ڈیفالٹ 65 سیکنڈ (تھوڑا اضافی بفر کے ساتھ)
            if "daily limit" in message:
                duration = 24 * 60 * 60  # 24 گھنٹے
                logger.critical(f"API کلید {api_key[:8]}... اپنی یومیہ حد تک پہنچ گئی ہے!")
            
            logger.warning(f"API کلید {api_key[:8]}... کی حد ختم ہو گئی۔ اسے {duration} سیکنڈ کے لیے محدود کیا جا رہا ہے۔")
            key_manager.mark_key_as_limited(api_key, duration_seconds=duration)
            
            # 1 سیکنڈ انتظار کریں اور دوسری کلید کے ساتھ دوبارہ کوشش کریں
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

# get_current_price_twelve_data فنکشن کو بھی اسی طرح اپ ڈیٹ کیا جا سکتا ہے اگر ضرورت ہو
async def get_current_price_twelve_data(symbol: str, client: httpx.AsyncClient) -> Optional[float]:
    """
    کسی جوڑے کی موجودہ قیمت حاصل کرتا ہے۔
    """
    api_key = key_manager.get_api_key()
    if not api_key:
        return None
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={api_key}"
    try:
        response = await client.get(url, timeout=10)
        if response.status_code == 429:
            key_manager.mark_key_as_limited(api_key, duration_seconds=65) # یہاں بھی سادہ پابندی
            await asyncio.sleep(1)
            return await get_current_price_twelve_data(symbol, client)
        response.raise_for_status()
        data = response.json()
        return float(data.get("price")) if data.get("price") else None
    except Exception:
        return None
        
