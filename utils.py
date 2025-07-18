import os
import httpx
from fastapi import HTTPException

# API کلید کو یہاں بھی حاصل کریں
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

async def fetch_twelve_data_ohlc(symbol: str, timeframe: str, output_size: int = 100):
    """Twelve Data API سے OHLCV ڈیٹا حاصل کرتا ہے۔"""
    if not TWELVE_DATA_API_KEY:
        # یہاں پرنٹ کریں کیونکہ یہ ایک پس منظر کا فنکشن ہے
        print("CRITICAL ERROR in utils: API key for data provider is not configured.")
        # اور ایک خالی فہرست واپس کریں تاکہ ایپ کریش نہ ہو
        return []

    interval_map = {"1m": "1min", "5m": "5min", "15m": "15min", "1h": "1h"}
    interval = interval_map.get(timeframe)
    if not interval:
        print(f"Unsupported timeframe requested in utils: {timeframe}")
        return []

    url = f"https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": output_size,
        "apikey": TWELVE_DATA_API_KEY,
        "timezone": "UTC"
    }
    
    print(f"UTILS/TWELVE_DATA: Fetching time series for {symbol} ({interval})...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "ok" or "values" not in data:
            print(f"Twelve Data API returned an error in utils: {data.get('message', 'Unknown error')}")
            return []

        candles = []
        for item in reversed(data["values"]):
            candles.append({
                "datetime": item["datetime"],
                "open": float(item["open"]),
                "high": float(item["high"]),
                "low": float(item["low"]),
                "close": float(item["close"]),
                "volume": int(item.get("volume", 0))
            })
        
        return candles
    except Exception as e:
        print(f"CRITICAL ERROR in utils.fetch_twelve_data_ohlc: {e}")
        return []
              
