# filename: utils.py

import os
import time
# --- اہم اور حتمی اصلاح: 'Optional' کو 'typing' سے امپورٹ کیا گیا ---
from typing import List, Optional, Dict
import httpx
import asyncio
from datetime import datetime # --- datetime کو بھی امپورٹ کیا گیا ---

class KeyManager:
    def __init__(self):
        self.twelve_data_keys: List[str] = []
        self.limited_keys: Dict[str, float] = {}
        self.marketaux_api_key: Optional[str] = os.getenv("MARKETAUX_API_TOKEN", None)
        self.load_twelve_data_keys()

    def load_twelve_data_keys(self):
        api_keys_str = os.getenv("TWELVE_DATA_API_KEYS", "")
        self.twelve_data_keys = [key.strip() for key in api_keys_str.split(',') if key.strip()]
        if not hasattr(self, '_printed_key_count'):
            print(f"--- KeyManager Initialized: Found {len(self.twelve_data_keys)} Twelve Data key(s). ---")
            if self.marketaux_api_key:
                print("--- KeyManager Initialized: MarketAux API key FOUND. ---")
            else:
                print("--- KeyManager WARNING: MarketAux API key NOT FOUND. ---")
            self._printed_key_count = True

    def get_twelve_data_api_key(self) -> Optional[str]:
        current_time = time.time()
        for key in self.twelve_data_keys:
            if key not in self.limited_keys or current_time - self.limited_keys.get(key, 0) > 60:
                if key in self.limited_keys:
                    del self.limited_keys[key]
                return key
        return None

    def mark_key_as_limited(self, key: str):
        if key in self.twelve_data_keys:
            print(f"--- KeyManager INFO: Twelve Data API key limit reached for key ending in ...{key[-4:]}. Rotating. ---")
            self.limited_keys[key] = time.time()
            
    def get_marketaux_api_key(self) -> Optional[str]:
        return self.marketaux_api_key

# key_manager کا ایک واحد انسٹنس بنائیں
key_manager = KeyManager()

def get_available_pairs():
    today = datetime.utcnow().weekday()
    if today >= 5: # ہفتہ (5) اور اتوار (6)
        return ["BTC/USD"]
    return ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]

async def fetch_twelve_data_ohlc(symbol: str, timeframe: str, size: int) -> Optional[list]:
    api_key = key_manager.get_twelve_data_api_key()
    if not api_key:
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
            return None
            
        return data['values'][::-1]
    except Exception:
        return None

async def get_current_price_twelve_data(symbol: str, client: httpx.AsyncClient) -> Optional[float]:
    api_key = key_manager.get_twelve_data_api_key()
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
            
