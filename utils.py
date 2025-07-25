# filename: utils.py

# ... (باقی تمام امپورٹس اور کوڈ ویسا ہی رہے گا) ...

async def fetch_twelve_data_ohlc(symbol: str) -> Optional[List[Candle]]: # واپسی کی قسم کو List[Candle] میں تبدیل کیا گیا
    """
    TwelveData API سے OHLC کینڈلز لاتا ہے اور انہیں Pydantic ماڈلز کی فہرست کے طور پر واپس کرتا ہے۔
    """
    api_key = key_manager.get_api_key()
    if not api_key:
        logger.warning("کوئی بھی Twelve Data API کلید دستیاب نہیں۔")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={PRIMARY_TIMEFRAME}&outputsize={CANDLE_COUNT}&apikey={api_key}"
    logger.info(f"[{symbol}] کے لیے Twelve Data API سے ڈیٹا حاصل کیا جا رہا ہے...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        
        if response.status_code == 429:
            logger.warning(f"API کلید کی حد ختم ہو گئی۔ کلید کو گھمایا جا رہا ہے۔")
            key_manager.mark_key_as_limited(api_key)
            await asyncio.sleep(1)
            return await fetch_twelve_data_ohlc(symbol)

        response.raise_for_status()
        data = response.json()
        
        if "values" not in data or data.get("status") != "ok":
            error_message = data.get("message", "کوئی خرابی کا پیغام نہیں")
            logger.warning(f"[{symbol}] کے لیے Twelve Data API نے خرابی واپس کی: {error_message}")
            return None

        validated_data = TwelveDataTimeSeries.model_validate(data)
        
        logger.info(f"[{symbol}] کے لیے کامیابی سے {len(validated_data.values)} کینڈلز حاصل کی گئیں۔")
        
        # --- اہم اور حتمی تبدیلی یہاں ہے ---
        # اب ہم Pydantic ماڈلز کو براہ راست واپس بھیج رہے ہیں، ڈکشنری میں تبدیل کیے بغیر
        return validated_data.values[::-1]
            
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے نامعلوم خرابی: {e}", exc_info=True)
        return None

# ... (باقی تمام کوڈ ویسا ہی رہے گا) ...
