# filename: utils.py

import asyncio
import logging
from typing import List, Optional, Dict, Any

import httpx

# مقامی امپورٹس
from key_manager import key_manager
from schemas import TwelveDataTimeSeries, Candle
# مرکزی کنفیگریشن ماڈیولز سے سیٹنگز درآمد کریں
from config import trading_settings

logger = logging.getLogger(__name__)

# --- کنفیگریشن سے متغیرات ---
PRIMARY_TIMEFRAME = trading_settings.PRIMARY_TIMEFRAME
# تجزیے کے لیے 100 مکمل کینڈلز کو یقینی بنانے کے لیے 101 کی درخواست کریں
CANDLE_COUNT = trading_settings.CANDLE_COUNT + 1

# --- API کال کے لیے مستقل اقدار ---
API_TIMEOUT = 20  # سیکنڈز
MAX_RETRIES = 2  # دوبارہ کوشش کی زیادہ سے زیادہ تعداد
RETRY_DELAY = 5   # سیکنڈز

async def _make_api_request(url: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    httpx کا استعمال کرتے ہوئے ایک محفوظ اور قابلِ اعتماد API درخواست کرتا ہے،
    جس میں دوبارہ کوشش کی منطق بھی شامل ہے۔
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=API_TIMEOUT)

            # شرح کی حد کی خرابی کو ہینڈل کریں
            if response.status_code == 429:
                data = response.json()
                is_daily = "day" in data.get("message", "").lower()
                key_manager.report_key_issue(api_key, is_daily_limit=is_daily)
                logger.warning(f"API کی شرح کی حد سے تجاوز کر گیا ہے۔ کلید: {api_key[:8]}...")
                return None  # اس کلید کے ساتھ دوبارہ کوشش نہ کریں

            # دیگر HTTP غلطیوں کے لیے اسٹیٹس کوڈ چیک کریں
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"API سے HTTP خرابی: {e.response.status_code} - {e.response.text} | URL: {url}")
            # کلائنٹ کی غلطیوں (4xx) پر دوبارہ کوشش نہ کریں
            if 400 <= e.response.status_code < 500:
                break
        except (httpx.RequestError, asyncio.TimeoutError) as e:
            logger.warning(f"API درخواست میں نیٹ ورک کی خرابی: {e} | کوشش {attempt + 1}/{MAX_RETRIES + 1}")
        except Exception as e:
            logger.error(f"API درخواست میں غیر متوقع خرابی: {e}", exc_info=True)
            break  # غیر متوقع خرابی پر دوبارہ کوشش نہ کریں

        if attempt < MAX_RETRIES:
            await asyncio.sleep(RETRY_DELAY)

    return None

async def get_real_time_quotes(symbols: List[str]) -> Optional[Dict[str, Any]]:
    """
    دی گئی علامتوں کی فہرست کے لیے TwelveData API سے تازہ ترین کوٹس حاصل کرتا ہے۔
    یہ فنکشن 'گارڈین' کیز استعمال کرتا ہے جو نگرانی کے لیے مخصوص ہیں۔
    """
    if not symbols:
        return {}

    api_key = key_manager.get_guardian_key()
    if not api_key:
        logger.warning("نگرانی کے لیے کوئی API کلید دستیاب نہیں۔ کوٹس حاصل نہیں کیے جا رہے۔")
        return None

    symbol_str = ",".join(symbols)
    url = f"https://api.twelvedata.com/quote?symbol={symbol_str}&apikey={api_key}"
    
    data = await _make_api_request(url, api_key)
    if not data:
        return None

    quotes = {}
    # API کے جواب کی مختلف ساختوں کو ہینڈل کریں
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

async def fetch_twelve_data_ohlc(symbol: str) -> Optional[List[Candle]]:
    """
    TwelveData API سے OHLC کینڈلز لاتا ہے، ہر کینڈل میں علامت کا نام شامل کرتا ہے،
    اور یقینی بناتا ہے کہ صرف مکمل شدہ کینڈلز واپس کی جائیں۔
    یہ فنکشن 'ہنٹر' کیز استعمال کرتا ہے جو نئے سگنلز کی تلاش کے لیے ہیں۔
    """
    api_key = key_manager.get_hunter_key()
    if not api_key:
        logger.warning(f"[{symbol}] OHLC ڈیٹا کے لیے کوئی API کلید دستیاب نہیں۔")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={PRIMARY_TIMEFRAME}&outputsize={CANDLE_COUNT}&apikey={api_key}"
    
    data = await _make_api_request(url, api_key)
    if not data:
        return None

    try:
        if data.get("status") != "ok":
            logger.warning(f"[{symbol}] کے لیے Twelve Data API نے خرابی واپس کی: {data.get('message', 'نامعلوم خرابی')}")
            return None

        validated_data = TwelveDataTimeSeries.model_validate(data)
        
        # API سے آنے والی فہرست کو پہلے تاریخ کے مطابق ترتیب دیں (نئی سے پرانی)
        sorted_values = sorted(validated_data.values, key=lambda x: x.datetime, reverse=True)
        
        # سب سے حالیہ (نامکمل) کینڈل کو ہٹا دیں اور صرف مطلوبہ تعداد (100) لیں
        completed_candles_raw = sorted_values[1:trading_settings.CANDLE_COUNT + 1]

        enriched_candles = []
        for candle in completed_candles_raw:
            candle.symbol = symbol
            enriched_candles.append(candle)

        # کینڈلز کو واپس پرانی سے نئی کی ترتیب میں کریں تاکہ تجزیہ درست ہو
        return enriched_candles[::-1]

    except Exception as e:
        logger.error(f"[{symbol}] کے لیے OHLC ڈیٹا کو پارس کرنے میں خرابی: {e}", exc_info=True)
        return None
        
