import logging
from tenacity import retry, stop_after_attempt, wait_fixed, before_sleep_log

# ... (باقی امپورٹس) ...

# Configure logging for tenacity
RETRY_LOG = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3),  # Retry up to 3 times
    wait=wait_fixed(2),          # Wait 2 seconds between retries
    before_sleep=before_sleep_log(RETRY_LOG, logging.WARNING) # Log before retrying
)
async def fetch_twelve_data_ohlc(symbol: str, timeframe: str, output_size: int) -> Optional[List[Dict]]:
    """
    Fetches OHLC data from Twelve Data API for a given symbol and timeframe.
    This function will automatically retry on failure.
    """
    api_key = key_manager_instance.get_twelve_data_api_key()
    if not api_key:
        logging.error("Cannot fetch OHLC data: No available Twelve Data API key.")
        return None
    
    url = f"https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": timeframe,
        "apikey": api_key,
        "outputsize": output_size
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            
            data = response.json()
            if data.get('status') == 'ok' and 'values' in data:
                return data['values']
            else:
                logging.warning(f"Twelve Data API returned non-ok status for {symbol}: {data.get('message', '')}")
                if "rate limit" in data.get('message', '').lower():
                    key_manager_instance.mark_key_as_limited(api_key)
                return None
                
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429: # Too Many Requests
            logging.warning(f"Rate limit hit for key. Marking as limited. Symbol: {symbol}")
            key_manager_instance.mark_key_as_limited(api_key)
        # The exception will be re-raised, and tenacity will handle the retry
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred in fetch_twelve_data_ohlc for {symbol}: {e}")
        # Re-raise to allow tenacity to handle it
        raise

    return None
    
