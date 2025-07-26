# filename: utils.py

import os
import httpx
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from key_manager import KeyManager
from schemas import TwelveDataTimeSeries, Candle

logger = logging.getLogger(__name__)
key_manager = KeyManager()

# --- کنفیگریشن ---
AVAILABLE_PAIRS_WEEKDAY = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
AVAILABLE_PAIRS_WEEKEND = ["BTC/USD"]
CANDLE_COUNT = 100

def get_available_pairs() -> List[str]:
    """ہفتے کے دن کی بنیاد پر دستیاب جوڑے واپس کرتا ہے۔"""
    today = datetime.utcnow().weekday()
    return AVAILABLE_PAIRS_WEEKEND if today >= 5 else AVAILABLE_PAIRS_WEEKDAY

async def fetch_twelve_data_ohlc(symbol: str, timeframe: str) -> Optional[List[Dict[str, Any]]]:
    """
    TwelveData API سے OHLC کینڈلز لاتا ہے اور انہیں ڈکشنری کی فہرست کے طور پر واپس کرتا ہے۔
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
            key_manager.mark_key_as_limited(api_key)
            await asyncio.sleep(1)
            return await fetch_twelve_data_ohlc(symbol, timeframe)

        response.raise_for_status()
        data = response.json()
        
        if "values" not in data or data.get("status") != "ok":
            error_message = data.get("message", "کوئی خرابی کا پیغام نہیں")
            logger.warning(f"[{symbol}] کے لیے Twelve Data API نے خرابی واپس کی: {error_message}")
            return None

        # ★★★ خودکار اصلاح: Pydantic ماڈل کی توثیق کے بعد اسے معیاری ڈکشنری میں تبدیل کیا گیا ★★★
        validated_data = TwelveDataTimeSeries.model_validate(data)
        candle_dicts = [c.model_dump() for c in validated_data.values]
        
        logger.info(f"[{symbol}] کے لیے کامیابی سے {len(candle_dicts)} کینڈلز حاصل کی گئیں۔")
        return candle_dicts[::-1] # ڈیٹا کو پرانے سے نئے کی ترتیب میں واپس کریں
            
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے نامعلوم خرابی: {e}", exc_info=True)
        return None

async def fetch_binance_ohlc(symbol: str, timeframe: str) -> Optional[List[Dict[str, Any]]]:
    """
    Binance/KuCoin کے لیے تاریخی OHLC کینڈلز لاتا ہے اور انہیں ڈکشنری کی فہرست کے طور پر واپس کرتا ہے۔
    """
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={timeframe}&limit={CANDLE_COUNT}"
    logger.info(f"[{symbol}] کے لیے Binance API سے تاریخی ڈیٹا حاصل کیا جا رہا ہے...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
        response.raise_for_status()
        klines = response.json()
        
        # ★★★ خودکار اصلاح: ڈیٹا کو معیاری ڈکشنری کی شکل میں تبدیل کیا گیا ★★★
        candle_dicts = [{
            "datetime": datetime.fromtimestamp(k[0] / 1000).isoformat(),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5])
        } for k in klines]
        
        logger.info(f"[{symbol}] کے لیے کامیابی سے {len(candle_dicts)} تاریخی کینڈلز حاصل کی گئیں۔")
        return candle_dicts
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے تاریخی ڈیٹا حاصل کرنے میں ناکامی: {e}", exc_info=True)
        return None

async def get_current_price_twelve_data(symbol: str, client: httpx.AsyncClient) -> Optional[float]:
    """کسی جوڑے کی موجودہ قیمت حاصل کرتا ہے۔"""
    api_key = key_manager.get_api_key()
    if not api_key: return None
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={api_key}"
    try:
        response = await client.get(url, timeout=10)
        if response.status_code == 429:
            key_manager.mark_key_as_limited(api_key)
            await asyncio.sleep(1)
            return await get_current_price_twelve_data(symbol, client)
        response.raise_for_status()
        data = response.json()
        return float(data.get("price")) if data.get("price") else None
    except Exception:
        return None
            
