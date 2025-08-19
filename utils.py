# filename: utils.py

import asyncio
import logging
from typing import List, Optional, Dict, Any

import httpx
from pydantic import ValidationError
import pandas as pd

from key_manager import key_manager
from schemas import TwelveDataTimeSeries, Candle

logger = logging.getLogger(__name__)

async def get_real_time_quotes(symbols: List[str]) -> Optional[Dict[str, Any]]:
    """
    ہر علامت کے لیے اس کی مخصوص API کلید استعمال کرتے ہوئے متوازی طور پر قیمتیں حاصل کرتا ہے۔
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

async def fetch_twelve_data_ohlc(symbol: str, timeframe: str, output_size: int) -> Optional[List[Candle]]:
    """
    Twelve Data API سے OHLCV ڈیٹا حاصل کرتا ہے۔
    """
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
        
        # API اکثر نامکمل موجودہ کینڈل بھیجتی ہے، اسے ہٹانے کے لیے ڈیٹا کو ترتیب دیں
        sorted_values = sorted(validated_data.values, key=lambda x: x.datetime, reverse=True)
        completed_candles_raw = sorted_values[1:] if len(sorted_values) > 1 else sorted_values
        
        enriched_candles = []
        for candle_data in completed_candles_raw:
            # ہر کینڈل میں علامت شامل کریں تاکہ ڈیٹا فریم میں استعمال ہو سکے
            enriched_candles.append(candle_data.copy(update={"symbol": symbol}))

        # ڈیٹا کو پرانے سے نئے کی طرف ترتیب دیں
        return enriched_candles[::-1]

    except ValidationError as e:
        logger.error(f"[{symbol}] کے لیے Twelve Data API سے آنے والے ڈیٹا کو پارس کرنے میں خرابی: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"[{symbol}] کے لیے OHLC ڈیٹا حاصل کرنے میں HTTP خرابی: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے OHLC ڈیٹا حاصل کرنے میں نامعلوم خرabi: {e}", exc_info=True)
        return None

def convert_candles_to_dataframe(candles: List[Candle]) -> pd.DataFrame:
    """
    کینڈلز کی فہرست کو ایک صاف ستھرے پانڈاز ڈیٹا فریم میں تبدیل کرتا ہے،
    اور یقینی بناتا ہے کہ تمام عددی کالمز کی قسم درست ہے۔
    """
    if not candles:
        return pd.DataFrame()
    
    # ڈیٹا فریم بنائیں
    df = pd.DataFrame([c.dict() for c in candles])
    
    # --- حتمی حل یہاں ہے ---
    # تمام ضروری عددی کالمز کی فہرست
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    
    for col in numeric_cols:
        if col in df.columns:
            # pd.to_numeric کا استعمال کریں جو خود بخود اور محفوظ طریقے سے قسم تبدیل کرتا ہے
            # errors='coerce' اس بات کو یقینی بنائے گا کہ اگر کوئی غلط قدر ہو تو اسے NaN سے تبدیل کر دیا جائے
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # اگر کسی بھی اہم کالم (OHLC) میں کوئی NaN قدر ہو تو اس قطار کو ہٹا دیں
    df.dropna(subset=['open', 'high', 'low', 'close'], inplace=True)
    
    return df
                                 
