import os
import httpx
import json
from datetime import datetime
from typing import List, Dict, Optional

# ہمارے پروجیکٹ کے ماڈیولز
from key_manager import get_api_key, mark_key_as_limited

# --- نیا فنکشن جو غائب تھا ---
def get_available_pairs() -> List[str]:
    """
    دن کے حساب سے اسکین کرنے کے لیے دستیاب جوڑوں کی فہرست واپس کرتا ہے۔
    ہفتے کے آخر میں صرف کرپٹو، باقی دن فاریکس اور کرپٹو۔
    """
    today = datetime.utcnow().weekday()
    # ہفتہ (5) اور اتوار (6)
    if today == 5 or today == 6:
        print("Weekend detected. Scanning crypto pairs only.")
        return ["BTC/USD"]
    else:
        print("Weekday detected. Scanning all pairs.")
        return ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]

async def fetch_twelve_data_ohlc(symbol: str, timeframe: str, output_size: int = 100) -> Optional[List[Dict]]:
    """
    Twelve Data API سے OHLC ڈیٹا حاصل کرتا ہے۔
    """
    api_key = get_api_key()
    if not api_key:
        print("All API keys have reached their limits.")
        return None

    url = f"https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": timeframe,
        "apikey": api_key,
        "outputsize": output_size,
        "timezone": "UTC"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=20)
        
        data = response.json()

        if response.status_code == 429 or (isinstance(data, dict) and data.get("code") == 429):
            print(f"API key limit reached for key ending in ...{api_key[-4:]}. Rotating.")
            mark_key_as_limited(api_key)
            # ایک اور کلید کے ساتھ دوبارہ کوشش کریں
            return await fetch_twelve_data_ohlc(symbol, timeframe, output_size)

        response.raise_for_status()

        if "values" not in data:
            print(f"Warning: 'values' not in response for {symbol}. Response: {data}")
            return None

        # ڈیٹا کو صحیح فارمیٹ میں تبدیل کریں (پرانا پہلے)
        candles = data["values"]
        candles.reverse()
        
        # کالمز کو اپنے فارمیٹ میں تبدیل کریں
        formatted_candles = [
            {
                "datetime": item["datetime"],
                "open": float(item["open"]),
                "high": float(item["high"]),
                "low": float(item["low"]),
                "close": float(item["close"]),
                "volume": int(item.get("volume", 0))
            }
            for item in candles
        ]
        return formatted_candles

    except httpx.HTTPStatusError as e:
        print(f"HTTP Error fetching OHLC for {symbol}: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in fetch_twelve_data_ohlc for {symbol}: {e}")
        return None
        
