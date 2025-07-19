# utils.py

import httpx
import asyncio
from datetime import datetime
from typing import Optional

# --- اہم تبدیلی: KeyManager کلاس کو براہ راست امپورٹ کریں ---
from key_manager import KeyManager

# --- سب سے اہم تبدیلی: key_manager کی مثال یہاں بنائیں ---
# چونکہ utils.py ایک بنیادی فائل ہے جسے ہر کوئی استعمال کرتا ہے،
# یہاں مثال بنانا سب سے محفوظ ہے اور سرکلر امپورٹ کو توڑتا ہے۔
key_manager = KeyManager()

def get_available_pairs():
    today = datetime.utcnow().weekday()
    if today >= 5: # Saturday or Sunday
        return ["BTC/USD"]
    return ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]

async def fetch_twelve_data_ohlc(symbol: str, timeframe: str, size: int) -> Optional[list]:
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
            await asyncio.sleep(1)
            return await fetch_twelve_data_ohlc(symbol, timeframe, size)
        
        response.raise_for_status()
        data = response.json()
        
        if 'values' not in data:
            print(f"--- UTILS WARNING: 'values' not in response for {symbol}. Response: {data} ---")
            return None
            
        return data['values'][::-1]
    except Exception as e:
        print(f"--- UTILS UNEXPECTED ERROR fetching {symbol}: {e} ---")
        return None

async def get_current_price_twelve_data(symbol: str, client: httpx.AsyncClient) -> Optional[float]:
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
        
