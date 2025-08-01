# filename: utils.py

import os
import httpx
import logging
from typing import List, Optional, Dict, Any

from key_manager import key_manager
from schemas import TwelveDataTimeSeries, Candle
from config import API_CONFIG

logger = logging.getLogger(__name__)

PRIMARY_TIMEFRAME = API_CONFIG["PRIMARY_TIMEFRAME"]
CANDLE_COUNT = API_CONFIG["CANDLE_COUNT"] + 1

async def get_real_time_quotes(symbols: List[str]) -> Optional[Dict[str, Any]]:
    if not symbols:
        return {}

    api_key = key_manager.get_guardian_key()
    if not api_key:
        logger.warning("No guardian API key available.")
        return None

    symbol_str = ",".join(symbols)
    url = f"https://api.twelvedata.com/quote?symbol={symbol_str}&apikey={api_key}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=20)
        if response.status_code == 429:
            logger.warning("API limit exceeded (429).")
            return None
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching real-time quotes: {e}", exc_info=True)
        return None

def fetch_twelve_data_ohlc(symbol: str) -> Optional[List[Candle]]:
    api_key = key_manager.get_main_key()
    if not api_key:
        logger.warning("No main API key available.")
        return None

    url = (
        f"https://api.twelvedata.com/time_series?"
        f"symbol={symbol}&interval={PRIMARY_TIMEFRAME}&outputsize={CANDLE_COUNT}&apikey={api_key}"
    )

    try:
        response = httpx.get(url, timeout=30)
        if response.status_code != 200:
            logger.warning(f"TwelveData API response code: {response.status_code}")
            return None

        data = response.json()
        candles_raw = data.get("values", [])
        if not candles_raw or len(candles_raw) < 3:
            logger.info(f"Insufficient candle data for: {symbol}")
            return None

        candles: List[Candle] = [
            Candle(
                datetime=entry["datetime"],
                open=float(entry["open"]),
                high=float(entry["high"]),
                low=float(entry["low"]),
                close=float(entry["close"]),
                volume=float(entry.get("volume", 0.0)),
            )
            for entry in candles_raw
        ]
        return candles[:-1]
    except Exception as e:
        logger.error(f"Error fetching OHLC data: {e}", exc_info=True)
        return None
