import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

import httpx
from pydantic import ValidationError
import pandas as pd

from key_manager import key_manager
from schemas import TwelveDataTimeSeries, Candle
# ★★★ نیا امپورٹ ★★★
from config import api_settings

logger = logging.getLogger(__name__)

# ... (get_real_time_quotes اور fetch_twelve_data_ohlc فنکشنز پہلے کی طرح رہیں گے) ...

async def get_real_time_quotes(symbols: List[str]) -> Optional[Dict[str, Any]]:
    if not symbols:
        return {}
    unique_symbols = sorted(list(set(symbols)))
    async def fetch_single_quote(symbol: str) -> Optional[Dict[str, Any]]:
        api_key = key_manager.get_key_for_pair(symbol)
        if not api_key:
            logger.warning(f"[{symbol}] کے لیے قیمت حاصل کرنے میں ناکامی: کوئی API کلید نہیں۔")
            return None
        url = f"https://api.twelvedata.com/quote?symbol={symbol}&apikey={api_key}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=15)
            if response.status_code == 429:
                logger.warning(f"[{symbol}] کی کلید '...{api_key[-4:]}' ریٹ لمیٹڈ ہے۔")
                return None
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and 'close' in data:
                data['symbol'] = symbol
                data['price'] = data['close']
                return data
            else:
                logger.warning(f"[{symbol}] کے لیے غیر متوقع یا نامکمل جواب موصول ہوا: {data}")
                return None
        except Exception as e:
            logger.error(f"[{symbol}] کے لیے قیمت حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
            return None
    tasks = [fetch_single_quote(s) for s in unique_symbols]
    results = await asyncio.gather(*tasks)
    all_quotes = {res['symbol']: res for res in results if res}
    if len(all_quotes) < len(unique_symbols):
        logger.warning(f"صرف {len(all_quotes)}/{len(unique_symbols)} جوڑوں کے لیے قیمتیں کامیابی سے حاصل کی گئیں۔")
    else:
        logger.info(f"تمام {len(all_quotes)} جوڑوں کے لیے قیمتیں کامیابی سے حاصل کی گئیں۔")
    return all_quotes

async def fetch_twelve_data_ohlc(symbol: str, timeframe: str, output_size: int) -> Optional[List[Candle]]:
    api_key = key_manager.get_key_for_pair(symbol)
    if not api_key:
        logger.warning(f"[{symbol}] OHLC کے لیے کوئی API کلید دستیاب نہیں۔")
        return None
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={timeframe}&outputsize={output_size}&apikey={api_key}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=20)
        if response.status_code == 429:
            logger.warning(f"[{symbol}] کی کلید '...{api_key[-4:]}' OHLC کے لیے ریٹ لمیٹڈ ہے۔")
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
            enriched_candles.append(candle_data.copy(update={"symbol": symbol}))
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

# ★★★ نیا فنکشن برائے قابل اعتماد حجم ★★★
async def fetch_polygon_volume_data(symbols: List[str], timeframe: str, candle_count: int) -> Optional[Dict[str, List[float]]]:
    """Polygon.io سے متعدد جوڑوں کے لیے قابل اعتماد حجم کا ڈیٹا حاصل کرتا ہے۔"""
    if not api_settings.POLYGON_API_KEY:
        logger.warning("Polygon API کلید دستیاب نہیں، حجم کا ڈیٹا حاصل نہیں کیا جا رہا۔")
        return None
    if not symbols:
        return {}

    # Polygon.io کے لیے ٹائم فریم کو تبدیل کریں (e.g., '15min' -> '15', 'minute')
    multiplier, timespan = 1, "minute"
    if "min" in timeframe:
        multiplier = int(timeframe.replace("min", ""))
        timespan = "minute"
    elif "hour" in timeframe:
        multiplier = int(timeframe.replace("hour", ""))
        timespan = "hour"

    # تاریخ کی حد کا حساب لگائیں
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30) # زیادہ ڈیٹا حاصل کریں تاکہ یقینی ہو کہ کینڈلز مل جائیں

    async def fetch_single_symbol_volume(symbol: str, client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
        # فاریکس جوڑوں کے لیے "C:" پریفکس شامل کریں
        polygon_symbol = f"C:{symbol.replace('/', '')}" if "/" in symbol else symbol
        
        url = (f"https://api.polygon.io/v2/aggs/ticker/{polygon_symbol}/range/{multiplier}/{timespan}/"
               f"{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}")
        params = {"apiKey": api_settings.POLYGON_API_KEY, "limit": candle_count + 5, "sort": "desc"}

        try:
            response = await client.get(url, params=params, timeout=20)
            if response.status_code == 429:
                logger.warning(f"[{symbol}] Polygon API ریٹ لمٹ پوری ہو گئی۔")
                return None
            response.raise_for_status()
            data = response.json()
            if data.get("resultsCount", 0) > 0:
                # حجم کی فہرست واپس کریں، تازہ ترین سے پرانی ترتیب میں
                volumes = [result.get('v', 0) for result in data.get('results', [])]
                return {"symbol": symbol, "volumes": volumes}
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"[{symbol}] کے لیے Polygon API سے خرابی: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"[{symbol}] کے لیے Polygon سے حجم حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
            return None

    all_volumes = {}
    async with httpx.AsyncClient() as client:
        tasks = [fetch_single_symbol_volume(s, client) for s in symbols]
        results = await asyncio.gather(*tasks)
    
    for res in results:
        if res and isinstance(res, dict):
            all_volumes[res["symbol"]] = res["volumes"]
            
    logger.info(f"Polygon.io سے {len(all_volumes)}/{len(symbols)} جوڑوں کے لیے حجم کا ڈیٹا کامیابی سے حاصل کیا گیا۔")
    return all_volumes

def convert_candles_to_dataframe(candles: List[Candle]) -> pd.DataFrame:
    if not candles:
        return pd.DataFrame()
    df = pd.DataFrame([c.dict() for c in candles])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df.dropna(subset=['open', 'high', 'low', 'close'], inplace=True)
    return df
        
