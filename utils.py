# filename: utils.py

import logging
from typing import List, Optional, Dict, Any

import httpx
from pydantic import ValidationError

# مقامی امپورٹس
from key_manager import key_manager
from schemas import TwelveDataTimeSeries, Candle
from config import api_settings

logger = logging.getLogger(__name__)

# --- کنفیگریشن سے متغیرات ---
PRIMARY_TIMEFRAME = api_settings.PRIMARY_TIMEFRAME
# ایک اضافی کینڈل حاصل کریں گے تاکہ نامکمل کو ہٹا سکیں
CANDLE_COUNT = api_settings.CANDLE_COUNT + 1

async def get_real_time_quotes(symbols: List[str]) -> Optional[Dict[str, Any]]:
    """
    دی گئی علامتوں کی فہرست کے لیے TwelveData API سے تازہ ترین کوٹس حاصل کرتا ہے۔
    یہ فنکشن مرکزی کی پول سے ایک کلید استعمال کرتا ہے۔
    """
    if not symbols:
        return {}

    # اصلاح: مرکزی get_key فنکشن کا استعمال
    api_key = key_manager.get_key()
    if not api_key:
        logger.warning("کوٹس حاصل کرنے کے لیے کوئی API کلید دستیاب نہیں۔")
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

    except httpx.HTTPStatusError as e:
        logger.error(f"کوٹس حاصل کرنے میں HTTP خرابی: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"کوٹس حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
        return None

async def fetch_twelve_data_ohlc(symbol: str) -> Optional[List[Candle]]:
    """
    TwelveData API سے OHLC کینڈلز لاتا ہے اور صرف مکمل شدہ کینڈلز واپس کرتا ہے۔
    یہ فنکشن مرکزی کی پول سے ایک کلید استعمال کرتا ہے۔
    """
    # اصلاح: مرکزی get_key فنکشن کا استعمال
    api_key = key_manager.get_key()
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
        
        # API سے آنے والی فہرست کو پہلے ترتیب دیں (نئی سے پرانی)
        sorted_values = sorted(validated_data.values, key=lambda x: x.datetime, reverse=True)
        
        # سب سے حالیہ کینڈل (جو نامکمل ہو سکتی ہے) کو ہٹا دیں
        completed_candles_raw = sorted_values[1:api_settings.CANDLE_COUNT + 1]

        enriched_candles = []
        for candle_data in completed_candles_raw:
            candle_data.symbol = symbol
            enriched_candles.append(candle_data)

        # کینڈلز کو واپس پرانی سے نئی کی ترتیب میں کریں تاکہ تجزیہ درست ہو
        return enriched_candles[::-1]

    except ValidationError as e:
        logger.error(f"[{symbol}] کے لیے Twelve Data API سے آنے والے ڈیٹا کو پارس کرنے میں خرابی: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"[{symbol}] کے لیے OHLC ڈیٹا حاصل کرنے میں HTTP خرابی: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے OHLC ڈیٹا حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
        return None
        
