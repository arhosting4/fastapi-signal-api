# filename: utils.py

import os
import httpx
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict

from key_manager import KeyManager
from schemas import TwelveDataTimeSeries, Candle

logger = logging.getLogger(__name__)
key_manager = KeyManager()

# --- کنفیگریشن ---
CANDLE_COUNT = 100 # ہر بار حاصل کی جانے والی کینڈلز کی تعداد

async def fetch_binance_ohlc(symbol: str, timeframe: str, limit: int = 100) -> Optional[List[Candle]]:
    """
    Binance API سے تاریخی OHLCV کینڈلز حاصل کرتا ہے۔
    """
    # Binance API کے لیے علامت کو فارمیٹ کریں (مثلاً 'BTC/USDT' سے 'BTCUSDT')
    formatted_symbol = symbol.replace('/', '')
    url = f"https://api.binance.com/api/v3/klines?symbol={formatted_symbol}&interval={timeframe}&limit={limit}"
    logger.info(f"[{symbol}] کے لیے Binance API سے {limit} کینڈلز حاصل کی جا رہی ہیں...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        # Binance کے ڈیٹا کو ہمارے معیاری 'Candle' اسکیمہ میں تبدیل کریں
        candles = [
            Candle(
                datetime=datetime.fromtimestamp(item[0] / 1000).isoformat(),
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[5])
            ) for item in data
        ]
        logger.info(f"[{symbol}] کے لیے کامیابی سے {len(candles)} کینڈلز حاصل کی گئیں۔")
        return candles

    except Exception as e:
        logger.error(f"[{symbol}] کے لیے Binance سے ڈیٹا حاصل کرنے میں خرابی: {e}", exc_info=True)
        return None

async def fetch_twelve_data_ohlc(symbol: str, timeframe: str) -> Optional[List[Candle]]:
    """
    TwelveData API سے OHLC کینڈلز لاتا ہے۔
    """
    api_key = key_manager.get_api_key()
    if not api_key:
        logger.warning("کوئی بھی Twelve Data API کلید دستیاب نہیں۔")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={timeframe}&outputsize={CANDLE_COUNT}&apikey={api_key}"
    logger.info(f"[{symbol}] کے لیے Twelve Data API سے ڈیٹا حاصل کیا جا رہا ہے...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        
        if response.status_code == 429:
            logger.warning(f"API کلید کی حد ختم ہو گئی۔ کلید کو گھمایا جا رہا ہے۔")
            key_manager.mark_key_as_limited(api_key)
            await asyncio.sleep(1)
            return await fetch_twelve_data_ohlc(symbol, timeframe)

        response.raise_for_status()
        data = response.json()
        
        if "values" not in data or data.get("status") != "ok":
            logger.warning(f"[{symbol}] کے لیے Twelve Data API نے خرابی واپس کی: {data.get('message', 'نامعلوم')}")
            return None

        validated_data = TwelveDataTimeSeries.model_validate(data)
        logger.info(f"[{symbol}] کے لیے کامیابی سے {len(validated_data.values)} کینڈلز حاصل کی گئیں۔")
        return validated_data.values[::-1] # ڈیٹا کو پرانے سے نئے کی طرف ترتیب دیں
            
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے Twelve Data سے ڈیٹا حاصل کرنے میں خرابی: {e}", exc_info=True)
        return None
        
