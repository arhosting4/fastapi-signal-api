# filename: utils.py

import os
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# --- اہم: KeyManager کو یہاں سے امپورٹ کریں ---
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
    """
    تجزیہ کے لیے دستیاب کرنسی کے جوڑوں کی فہرست فراہم کرتا ہے۔
    """
    return [
        "XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD",
        "USD/CAD", "USD/CHF", "NZD/USD"
    ]

async def fetch_twelve_data_ohlc(symbol: str, interval: str, outputsize: int) -> List[Dict[str, Any]]:
    """
    Twelve Data API سے OHLC (Open, High, Low, Close) ڈیٹا حاصل کرتا ہے۔
    """
    api_key = key_manager.get_key()
    if not api_key:
        print("--- UTILS ERROR: No available Twelve Data API keys. ---")
        return []

    url = f"https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": api_key,
        "timezone": "UTC"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=20)
        
        if response.status_code == 429: # اگر API کی حد پوری ہو گئی ہو
            print(f"--- UTILS WARNING: API key limit reached for key ending in ...{api_key[-4:]}. Switching key. ---")
            key_manager.invalidate_current_key()
            return await fetch_twelve_data_ohlc(symbol, interval, outputsize) # دوسری کی کے ساتھ دوبارہ کوشش کریں

        response.raise_for_status()
        data = response.json()

        if data.get("status") == "error":
            print(f"--- UTILS ERROR from Twelve Data API: {data.get('message')} ---")
            return []

        # ڈیٹا کو صحیح فارمیٹ میں تبدیل کرنا
        formatted_candles = []
        for c in data.get("values", []):
            formatted_candles.append({
                "datetime": c["datetime"],
                "open": float(c["open"]),
                "high": float(c["high"]),
                "low": float(c["low"]),
                "close": float(c["close"])
            })
        
        # API اکثر الٹا ڈیٹا بھیجتی ہے، اسے سیدھا کریں
        return sorted(formatted_candles, key=lambda x: x['datetime'])

    except httpx.HTTPStatusError as e:
        print(f"--- UTILS HTTP ERROR: Failed to fetch OHLC data for {symbol}. Status: {e.response.status_code} ---")
        return []
    except Exception as e:
        print(f"--- UTILS CRITICAL ERROR fetching OHLC: {e} ---")
        return []

# --- یہ گمشدہ فنکشن ہے جسے ہم شامل کر رہے ہیں ---
async def fetch_current_price_twelve_data(symbol: str, client: httpx.AsyncClient) -> Optional[float]:
    """
    Twelve Data API سے کسی علامت کی موجودہ قیمت حاصل کرتا ہے۔
    """
    api_key = key_manager.get_key()
    if not api_key:
        print("--- UTILS ERROR: No available Twelve Data API keys for real-time price. ---")
        return None
        
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={api_key}"
    try:
        response = await client.get(url, timeout=10)
        if response.status_code == 429:
            print(f"--- UTILS WARNING: API key limit reached for real-time price. Switching key. ---")
            key_manager.invalidate_current_key()
            return await fetch_current_price_twelve_data(symbol, client)

        response.raise_for_status()
        data = response.json()
        price = float(data.get("price"))
        return price
    except Exception as e:
        print(f"--- UTILS ERROR fetching real-time price for {symbol}: {e} ---")
        return None
    
