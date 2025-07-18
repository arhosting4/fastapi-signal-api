import os
import httpx
from datetime import datetime, timedelta

# API کلید
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

# --- نیا: کینڈل ڈیٹا کے لیے کیشنگ سسٹم ---
ohlc_cache = {}
OHLC_CACHE_DURATION_SECONDS = 60 # 1 منٹ کے لیے کینڈلز کو کیش کریں

async def fetch_twelve_data_ohlc(symbol: str, timeframe: str, output_size: int = 100):
    """
    Twelve Data API سے OHLCV ڈیٹا حاصل کرتا ہے۔
    اب یہ API کالز بچانے کے لیے کیشنگ کا استعمال کرتا ہے۔
    """
    now = datetime.utcnow()
    cache_key = f"{symbol}_{timeframe}"

    # 1. کیشے چیک کریں
    if cache_key in ohlc_cache:
        cached_candles, cache_time = ohlc_cache[cache_key]
        if now - cache_time < timedelta(seconds=OHLC_CACHE_DURATION_SECONDS):
            print(f"OHLC CACHE HIT: Returning cached candles for {cache_key}")
            return cached_candles

    # 2. اگر کیشے پرانی ہے یا موجود نہیں، تو API کال کریں
    print(f"OHLC CACHE MISS: Fetching fresh candles for {cache_key} from Twelve Data.")
    if not TWELVE_DATA_API_KEY:
        print("CRITICAL ERROR in utils: API key is not configured.")
        return []

    interval_map = {"1m": "1min", "5m": "5min", "15m": "15min", "1h": "1h"}
    interval = interval_map.get(timeframe)
    if not interval:
        print(f"Unsupported timeframe requested in utils: {timeframe}")
        return []

    url = f"https://api.twelvedata.com/time_series"
    params = {"symbol": symbol, "interval": interval, "outputsize": output_size, "apikey": TWELVE_DATA_API_KEY, "timezone": "UTC"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "ok" or "values" not in data:
            print(f"Twelve Data API error in utils: {data.get('message', 'Unknown error')}")
            return []

        candles = []
        for item in reversed(data["values"]):
            candles.append({"datetime": item["datetime"], "open": float(item["open"]), "high": float(item["high"]), "low": float(item["low"]), "close": float(item["close"]), "volume": int(item.get("volume", 0))})
        
        # 3. نئے ڈیٹا کو کیشے میں محفوظ کریں
        if candles:
            ohlc_cache[cache_key] = (candles, now)
        
        return candles
    except Exception as e:
        print(f"CRITICAL ERROR in utils.fetch_twelve_data_ohlc: {e}")
        return []
        
