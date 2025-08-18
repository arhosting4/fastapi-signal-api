import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

import httpx
import pandas as pd

from config import api_settings
from key_manager import key_manager

logger = logging.getLogger(__name__)

async def get_real_time_quotes(symbols: List[str]) -> Optional[Dict[str, Any]]:
    """
    Twelve Data API کا استعمال کرتے ہوئے متعدد جوڑوں کے لیے لائیو قیمتیں حاصل کرتا ہے۔
    """
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

# ★★★ حتمی، تیز، اور موثر ڈیٹا فنکشن ★★★
async def fetch_polygon_ohlcv(symbol: str, timeframe: str, candle_count: int) -> Optional[pd.DataFrame]:
    """
    Polygon.io سے صرف مطلوبہ تعداد میں تازہ ترین کینڈلز حاصل کرتا ہے۔
    """
    if not api_settings.POLYGON_API_KEY:
        logger.error("Polygon API کلید دستیاب نہیں، تاریخی ڈیٹا حاصل نہیں کیا جا سکتا۔")
        return None

    multiplier, timespan = 1, "minute"
    if "min" in timeframe:
        multiplier = int(timeframe.replace("min", ""))
    elif "hour" in timeframe:
        multiplier = int(timeframe.replace("hour", ""))
        timespan = "hour"

    polygon_symbol = f"C:{symbol.replace('/', '')}" if "/" in symbol else symbol
    
    # ایک مختصر تاریخ کی حد کا استعمال کریں تاکہ غیر ضروری ڈیٹا سے بچا جا سکے
    end_date = datetime.utcnow()
    # 15 منٹ کی 100 کینڈلز کے لیے تقریباً 2 دن کا ڈیٹا کافی ہوتا ہے، ہم 5 دن کا بفر رکھتے ہیں
    days_to_go_back = ((candle_count * multiplier) / (60*24)) * 1.5 + 5
    start_date = end_date - timedelta(days=days_to_go_back)

    url = (f"https://api.polygon.io/v2/aggs/ticker/{polygon_symbol}/range/{multiplier}/{timespan}/"
           f"{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}")
    
    # sort=desc اس بات کو یقینی بناتا ہے کہ ہمیں سب سے تازہ ترین کینڈلز ملیں
    params = {"apiKey": api_settings.POLYGON_API_KEY, "limit": candle_count, "sort": "desc"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=20)
        
        if response.status_code == 429:
            logger.warning(f"[{symbol}] Polygon API ریٹ لمٹ پوری ہو گئی۔")
            return None
        response.raise_for_status()
        data = response.json()

        if data.get("resultsCount", 0) > 0:
            results = data.get('results', [])
            df = pd.DataFrame(results)
            
            df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume', 't': 'datetime'}, inplace=True)
            df['datetime'] = pd.to_datetime(df['datetime'], unit='ms', utc=True)
            df['symbol'] = symbol
            df = df[['datetime', 'open', 'high', 'low', 'close', 'volume', 'symbol']]
            # چونکہ ہم نے sort=desc استعمال کیا ہے، ہمیں ڈیٹا کو دوبارہ سیدھا کرنا ہوگا
            df.sort_values(by='datetime', inplace=True)
            
            if not (df['high'] >= df['low']).all():
                logger.error(f"[{symbol}] Polygon سے ناقص ڈیٹا: 'high' قیمت 'low' سے کم ہے۔")
                return None

            logger.info(f"[{symbol}] Polygon.io سے {len(df)} کینڈلز کامیابی سے حاصل کی گئیں۔")
            return df
        else:
            logger.warning(f"[{symbol}] کے لیے Polygon.io سے کوئی ڈیٹا نہیں ملا۔")
            return None

    except httpx.HTTPStatusError as e:
        logger.error(f"[{symbol}] کے لیے Polygon API سے خرابی: {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے Polygon سے OHLCV حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
        return None
    
