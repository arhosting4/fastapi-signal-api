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
    if not symbols: return {}
    unique_symbols = sorted(list(set(symbols)))
    
    async def fetch_single_quote(symbol: str):
        api_key = key_manager.get_key_for_pair(symbol)
        if not api_key: return symbol, None
        url = f"https://api.twelvedata.com/quote?symbol={symbol}&apikey={api_key}"
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(url, timeout=15)
            if r.status_code == 429:
                logger.warning(f"[{symbol}] کی کلید ریٹ لمیٹڈ ہے۔")
                return symbol, None
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict) and ("symbol" in data or "code" not in data):
                 return symbol, data
            return symbol, None
        except Exception as e:
            logger.error(f"[{symbol}] کے لیے قیمت حاصل کرنے میں خرابی: {e}")
            return symbol, None

    tasks = [fetch_single_quote(s) for s in unique_symbols]
    results = await asyncio.gather(*tasks)
    return {symbol: data for symbol, data in results if data}

async def fetch_twelve_data_ohlc(symbol: str, timeframe: str, output_size: int) -> Optional[List[Candle]]:
    api_key = key_manager.get_key_for_pair(symbol)
    if not api_key: return None
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={timeframe}&outputsize={output_size}&apikey={api_key}"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=20)
        if r.status_code == 429: return None
        r.raise_for_status()
        validated_data = TwelveDataTimeSeries.model_validate(r.json())
        if validated_data.status != "ok": return None
        sorted_values = sorted(validated_data.values, key=lambda x: x.datetime, reverse=True)
        completed_candles_raw = sorted_values[1:] if len(sorted_values) > 1 else sorted_values
        return [c.copy(update={"symbol": symbol}) for c in completed_candles_raw][::-1]
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے OHLC ڈیٹا حاصل کرنے میں خرابی: {e}")
        return None

def convert_candles_to_dataframe(candles: List[Candle]) -> pd.DataFrame:
    if not candles: return pd.DataFrame()
    df = pd.DataFrame([c.dict() for c in candles])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df.dropna(subset=['open', 'high', 'low', 'close'], inplace=True)
    return df
    
