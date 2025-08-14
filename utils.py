# filename: utils.py

import asyncio
import logging
from typing import List, Optional, Dict, Any

import httpx
from pydantic import ValidationError
import pandas as pd

from key_manager import key_manager
from schemas import TwelveDataTimeSeries, Candle
from config import api_settings

logger = logging.getLogger(__name__)

# --- ریٹ لمیٹنگ سے بچنے کے لیے نئے پیرامیٹرز ---
API_CHUNK_SIZE = 8  # فی منٹ کی حد
API_DELAY_SECONDS = 65  # ہر گروپ کے بعد انتظار کا وقت (تھوڑا اضافی)

async def get_real_time_quotes(symbols: List[str]) -> Optional[Dict[str, Any]]:
    """
    دی گئی علامتوں کی فہرست کے لیے TwelveData API سے تازہ ترین کوٹس حاصل کرتا ہے۔
    یہ اب ریٹ لمیٹنگ سے بچنے کے لیے درخواستوں کو چھوٹے گروپس میں تقسیم کرتا ہے۔
    """
    if not symbols:
        return {}

    all_quotes = {}
    unique_symbols = sorted(list(set(symbols)))
    
    # علامتوں کو چھوٹے گروپس میں تقسیم کریں
    symbol_chunks = [unique_symbols[i:i + API_CHUNK_SIZE] for i in range(0, len(unique_symbols), API_CHUNK_SIZE)]
    
    logger.info(f"قیمتیں حاصل کرنے کے لیے علامتوں کو {len(symbol_chunks)} گروپس میں تقسیم کیا گیا ہے۔")

    for i, chunk in enumerate(symbol_chunks):
        api_key = key_manager.get_key()
        if not api_key:
            logger.warning("کوٹس حاصل کرنے کے لیے کوئی API کلید دستیاب نہیں۔")
            return None

        symbol_str = ",".join(chunk)
        url = f"https://api.twelvedata.com/quote?symbol={symbol_str}&apikey={api_key}"
        
        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"گروپ {i+1}/{len(symbol_chunks)} کے لیے قیمتیں حاصل کی جا رہی ہیں: {chunk}")
                response = await client.get(url, timeout=20)

            if response.status_code == 429:
                data = response.json()
                logger.warning(f"API ریٹ لمیٹ کا سامنا! پیغام: {data.get('message')}")
                # اگر فی منٹ کی حد ہے تو اگلے گروپ سے پہلے انتظار کریں
                if "minute" in data.get("message", "").lower():
                    await asyncio.sleep(API_DELAY_SECONDS)
                continue # اس گروپ کو چھوڑ کر اگلا شروع کریں

            response.raise_for_status()
            data = response.json()

            # جواب کو پروسیس کریں
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "symbol" in item:
                        all_quotes[item["symbol"]] = item
            elif isinstance(data, dict) and "symbol" in data:
                 all_quotes[data["symbol"]] = data
            elif isinstance(data, dict):
                 for symbol, details in data.items():
                    if isinstance(details, dict) and details.get("status") != "error":
                        all_quotes[symbol] = details
            
            # اگر مزید گروپس باقی ہیں تو انتظار کریں
            if i < len(symbol_chunks) - 1:
                logger.info(f"ریٹ لمیٹ سے بچنے کے لیے {API_DELAY_SECONDS} سیکنڈ انتظار کیا جا رہا ہے...")
                await asyncio.sleep(API_DELAY_SECONDS)

        except httpx.HTTPStatusError as e:
            logger.error(f"کوٹس حاصل کرنے میں HTTP خرابی: {e.response.status_code} - {e.response.text}")
            continue
        except Exception as e:
            logger.error(f"کوٹس حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
            continue
            
    return all_quotes

async def fetch_twelve_data_ohlc(symbol: str, timeframe: str, output_size: int) -> Optional[List[Candle]]:
    """
    مخصوص ٹائم فریم اور سائز کے لیے TwelveData API سے OHLC کینڈلز لاتا ہے۔
    """
    api_key = key_manager.get_key()
    if not api_key:
        logger.warning(f"[{symbol}] OHLC کے لیے کوئی API کلید دستیاب نہیں۔")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={timeframe}&outputsize={output_size}&apikey={api_key}"
    
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
        
        sorted_values = sorted(validated_data.values, key=lambda x: x.datetime, reverse=True)
        
        completed_candles_raw = sorted_values[1:] if len(sorted_values) > 1 else sorted_values

        enriched_candles = []
        for candle_data in completed_candles_raw:
            candle_data.symbol = symbol
            enriched_candles.append(candle_data)

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

def convert_candles_to_dataframe(candles: List[Candle]) -> pd.DataFrame:
    """کینڈل آبجیکٹس کی فہرست کو پانڈاس ڈیٹا فریم میں تبدیل کرتا ہے۔"""
    if not candles:
        return pd.DataFrame()
    
    df = pd.DataFrame([c.dict() for c in candles])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df.dropna(subset=['open', 'high', 'low', 'close'], inplace=True)
    return df
    
