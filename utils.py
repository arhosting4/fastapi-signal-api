import httpx
import asyncio
from datetime import datetime, timedelta
import os

from key_manager import key_manager

API_CACHE = {}
CACHE_DURATION = timedelta(minutes=10)

def get_available_pairs():
    today = datetime.utcnow().weekday()
    if today >= 5: # Saturday or Sunday
        return ["BTC/USD"]
    return ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]

async def fetch_twelve_data_ohlc(symbol, timeframe, size):
    api_key = key_manager.get_api_key()
    if not api_key:
        print("--- UTILS ERROR: No available API keys. ---")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={timeframe}&outputsize={size}&apikey={api_key}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        if response.status_code == 429:
            key_manager.mark_key_as_limited(api_key)
            return await fetch_twelve_data_ohlc(symbol, timeframe, size) # Retry with new key
        
        response.raise_for_status()
        data = response.json()
        
        if 'values' not in data:
            print(f"Warning: 'values' not in response for {symbol}. Response: {data}")
            return None
            
        return data['values'][::-1]
    except httpx.HTTPStatusError as e:
        print(f"--- UTILS HTTP ERROR fetching {symbol}: {e} ---")
        return None
    except Exception as e:
        print(f"--- UTILS UNEXPECTED ERROR fetching {symbol}: {e} ---")
        return None

async def get_current_price_twelve_data(symbol: str, client: httpx.AsyncClient):
    api_key = key_manager.get_api_key()
    if not api_key: return None
    
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={api_key}"
    try:
        response = await client.get(url, timeout=10)
        if response.status_code == 429:
            key_manager.mark_key_as_limited(api_key)
            return await get_current_price_twelve_data(symbol, client)
        
        response.raise_for_status()
        data = response.json()
        return float(data.get("price")) if data.get("price") else None
    except Exception:
        return None
        
