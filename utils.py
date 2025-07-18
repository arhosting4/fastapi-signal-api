import httpx
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# --- نیا: کلید مینیجر کو امپورٹ کریں ---
from key_manager import key_manager

# کینڈل ڈیٹا کے لیے کیشنگ
ohlc_cache = {}
CACHE_DURATION_OHLC = timedelta(seconds=55) # 55 سیکنڈ، تاکہ 1 منٹ کے وقفے پر ہمیشہ تازہ ڈیٹا ملے

async def fetch_twelve_data_ohlc(symbol: str, timeframe: str) -> Optional[List[Dict]]:
    """
    Twelve Data سے OHLC (کینڈل) ڈیٹا حاصل کرتا ہے، اب API کلید کی گردش کے ساتھ۔
    """
    cache_key = f"{symbol}-{timeframe}"
    now = datetime.utcnow()

    if cache_key in ohlc_cache:
        data, cache_time = ohlc_cache[cache_key]
        if now - cache_time < CACHE_DURATION_OHLC:
            return data

    # --- اہم تبدیلی: کلید مینیجر سے کلید حاصل کریں ---
    api_key = key_manager.get_current_key()
    if not api_key:
        print("OHLC Fetcher: No available API key.")
        return None

    url = f"https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": timeframe,
        "outputsize": 100, # تجزیے کے لیے کافی کینڈلز
        "apikey": api_key,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=15)
        
        # اگر کوٹہ ختم ہو جائے تو کلید کو گھمائیں
        if response.status_code == 429 or ("credits" in response.text and "run out" in response.text):
            print(f"API key limit reached for key ending in ...{api_key[-4:]}. Rotating key.")
            # --- اہم: اگلی کلید پر جائیں ---
            new_key = key_manager.rotate_to_next_key()
            if new_key:
                # نئی کلید کے ساتھ دوبارہ کوشش کریں
                print("Retrying with new key...")
                params["apikey"] = new_key
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params, timeout=15)
            else:
                # اگر کوئی نئی کلید نہیں ہے
                print("All keys exhausted. Cannot fetch OHLC data.")
                return None

        response.raise_for_status()
        data = response.json()

        if "values" in data:
            candles = [
                {
                    "datetime": v["datetime"],
                    "open": float(v["open"]),
                    "high": float(v["high"]),
                    "low": float(v["low"]),
                    "close": float(v["close"]),
                }
                for v in data["values"]
            ]
            candles.reverse() # API سے ڈیٹا الٹا آتا ہے، اسے سیدھا کریں
            ohlc_cache[cache_key] = (candles, now)
            return candles
        else:
            print(f"Warning: 'values' not in response for {symbol}. Response: {data}")
            return None

    except Exception as e:
        print(f"ERROR fetching OHLC for {symbol}: {e}")
        return None
        
