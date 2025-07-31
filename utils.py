# filename: utils.py

import os
import httpx
import logging
from typing import List, Optional, Dict, Any

from key_manager import key_manager
from schemas import TwelveDataTimeSeries, Candle
from config import API_CONFIG

logger = logging.getLogger(__name__)

# --- کنفیگریشن سے متغیرات ---
PRIMARY_TIMEFRAME = API_CONFIG["PRIMARY_TIMEFRAME"]
CANDLE_COUNT = API_CONFIG["CANDLE_COUNT"]

async def get_real_time_quotes(symbols: List[str]) -> Optional[Dict[str, Any]]:
    """
    دی گئی علامتوں کی فہرست کے لیے TwelveData API سے تازہ ترین کوٹس حاصل کرتا ہے۔
    یہ فنکشن 'گارڈین' کیز استعمال کرتا ہے۔
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
                    if isinstance(details, dict) and details.get("status") != "error":
                        quotes[symbol] = details
        
        return quotes

    except Exception as e:
        logger.error(f"کوٹس حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
        return None

# ★★★ مکمل طور پر اپ ڈیٹ شدہ اور ذہین فنکشن ★★★
async def fetch_twelve_data_ohlc(symbol: str) -> Optional[List[Candle]]:
    """
    TwelveData API سے OHLC کینڈلز لاتا ہے اور ہر کینڈل میں علامت کا نام شامل کرتا ہے۔
    یہ فنکشن 'ہنٹر' کیز استعمال کرتا ہے۔
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
        
        if "status" not in data or data.get("status") != "ok":
            logger.warning(f"[{symbol}] کے لیے Twelve Data API نے خرابی واپس کی: {data.get('message', 'نامعلوم خرابی')}")
            return None

        validated_data = TwelveDataTimeSeries.model_validate(data)
        
        enriched_candles = []
        for candle in validated_data.values:
            try:
                # ہر کینڈل میں علامت کا نام شامل کریں
                candle.symbol = symbol
                # قیمتوں کو فلوٹ میں تبدیل کریں
                candle.open = float(candle.open)
                candle.high = float(candle.high)
                candle.low = float(candle.low)
                candle.close = float(candle.close)
                enriched_candles.append(candle)
            except (ValueError, TypeError) as e:
                logger.warning(f"کینڈل ڈیٹا کو تبدیل کرنے میں خرابی: {e} - {candle.dict()}")
                continue

        # کینڈلز کو پرانی سے نئی کی ترتیب میں واپس کریں
        return enriched_candles[::-1]

    except Exception as e:
        logger.error(f"[{symbol}] کے لیے OHLC ڈیٹا حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
        return None
    
