# filename: utils.py
import os
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from key_manager import KeyManager

# Twelve Data کے لیے API کیز کا انتظام
twelve_data_keys = [
    os.getenv("TWELVE_DATA_API_KEY_1"),
    os.getenv("TWELVE_DATA_API_KEY_2"),
    os.getenv("TWELVE_DATA_API_KEY_3"),
    os.getenv("TWELVE_DATA_API_KEY_4"),
    os.getenv("TWELVE_DATA_API_KEY_5")
]
key_manager = KeyManager(keys=[k for k in twelve_data_keys if k])

def get_available_pairs() -> List[str]:
    return [
        "XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD",
        "USD/CAD", "USD/CHF", "NZD/USD"
    ]

async def fetch_twelve_data_ohlc(symbol: str, interval: str, outputsize: int) -> List[Dict[str, Any]]:
    api_key = key_manager.get_key()
    if not api_key:
        print("--- UTILS ERROR: No available Twelve Data API keys. ---")
        return []

    url = f"https://api.twelvedata.com/time_series"
    params = { "symbol": symbol, "interval": interval, "outputsize": outputsize, "apikey": api_key, "timezone": "UTC" }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=20)
        
        if response.status_code == 429:
            print(f"--- UTILS WARNING: API key limit reached. Switching key. ---")
            key_manager.invalidate_current_key()
            return await fetch_twelve_data_ohlc(symbol, interval, outputsize)

        response.raise_for_status()
        data = response.json()

        if data.get("status") == "error":
            return []

        formatted_candles = [
            {"datetime": c["datetime"], "open": float(c["open"]), "high": float(c["high"]), "low": float(c["low"]), "close": float(c["close"])}
            for c in data.get("values", [])
        ]
        return sorted(formatted_candles, key=lambda x: x['datetime'])

    except Exception as e:
        print(f"--- UTILS CRITICAL ERROR fetching OHLC: {e} ---")
        return []

async def fetch_current_price_twelve_data(symbol: str, client: httpx.AsyncClient) -> Optional[float]:
    api_key = key_manager.get_key()
    if not api_key:
        return None
        
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={api_key}"
    try:
        response = await client.get(url, timeout=10)
        if response.status_code == 429:
            key_manager.invalidate_current_key()
            return await fetch_current_price_twelve_data(symbol, client)

        response.raise_for_status()
        data = response.json()
        return float(data.get("price"))
    except Exception as e:
        print(f"--- UTILS ERROR fetching real-time price for {symbol}: {e} ---")
        return None
                                    
