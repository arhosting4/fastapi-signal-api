import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

import httpx
import pandas as pd

from config import api_settings
from key_manager import key_manager

logger = logging.getLogger(__name__)

# get_real_time_quotes فنکشن میں کوئی تبدیلی نہیں
async def get_real_time_quotes(symbols: List[str]) -> Optional[Dict[str, Any]]:
    # ... (یہ فنکشن پہلے جیسا ہی رہے گا) ...

# ★★★ حتمی، تیز، اور موثر ڈیٹا فنکشن ★★★
async def fetch_polygon_ohlcv(symbol: str, timeframe: str, candle_count: int) -> Optional[pd.DataFrame]:
    """
    Polygon.io سے صرف مطلوبہ تعداد میں تازہ ترین کینڈلز حاصل کرتا ہے۔
    یہ انتہائی تیز اور موثر ہے۔
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
    
    # ★★★ تبدیلی: اب ہم تاریخ کی حد کی بجائے صرف limit کا استعمال کرتے ہیں ★★★
    # URL سے تاریخ کی حد کو ہٹا دیا گیا ہے
    url = f"https://api.polygon.io/v2/aggs/ticker/{polygon_symbol}/prev"
    # limit پیرامیٹر کو candle_count کے برابر سیٹ کیا گیا ہے
    params = {"adjusted": "true", "limit": candle_count, "apiKey": api_settings.POLYGON_API_KEY}

    try:
        async with httpx.AsyncClient() as client:
            # یہ API پچھلی کینڈل کا ڈیٹا دیتی ہے، ہمیں اسے ٹائم سیریز کے لیے استعمال کرنا ہوگا
            # درست API اینڈ پوائنٹ: /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}
            # ہم limit کا استعمال نہیں کر سکتے، ہمیں پچھلی منطق پر واپس جانا ہوگا لیکن limit کے ساتھ
            
            end_date = datetime.utcnow()
            # اندازہ لگائیں کہ کتنے دن پیچھے جانا ہے
            # 15 منٹ کی کینڈل کے لیے، ایک دن میں 96 کینڈلز ہوتی ہیں۔ 100 کے لیے 2 دن کافی ہیں۔
            days_needed = (candle_count * multiplier) / (60 * 24) + 2 # تھوڑا اضافی بفر
            start_date = end_date - timedelta(days=days_needed)

            url = (f"https://api.polygon.io/v2/aggs/ticker/{polygon_symbol}/range/{multiplier}/{timespan}/"
                   f"{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}")
            
            # ★★★ حتمی تبدیلی: limit کو candle_count پر سیٹ کریں ★★★
            params = {"apiKey": api_settings.POLYGON_API_KEY, "limit": candle_count, "sort": "desc"}

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
    
