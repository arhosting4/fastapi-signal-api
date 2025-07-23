import os
import time
import logging
import httpx
from typing import List, Optional, Dict
from tenacity import retry, stop_after_attempt, wait_fixed, before_sleep_log

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
RETRY_LOG = logging.getLogger(__name__)

class KeyManager:
    """Manages API keys for external services."""
    def __init__(self):
        self.twelve_data_keys: List[str] = self._load_keys("TWELVE_DATA_API_KEYS", "TWELVE_DATA_API_KEY_")
        self.marketaux_api_key: Optional[str] = os.getenv("MARKETAUX_API_TOKEN")
        self.limited_keys: Dict[str, float] = {}
        self.current_key_index: int = 0
        
        if not self.marketaux_api_key:
            logging.warning("MARKETAUX_API_TOKEN not found. News features will be disabled.")

    def _load_keys(self, env_list_name: str, env_prefix: str) -> List[str]:
        """Loads keys from a comma-separated list or individual numbered env vars."""
        keys = set()
        keys_from_env_list = os.getenv(env_list_name)
        if keys_from_env_list:
            keys.update([key.strip() for key in keys_from_env_list.split(',') if key.strip()])
        
        i = 1
        while True:
            key = os.getenv(f"{env_prefix}{i}")
            if key:
                keys.add(key.strip())
                i += 1
            else:
                break
        
        loaded_keys = list(keys)
        if not loaded_keys:
            logging.warning(f"No API keys found for {env_list_name} or {env_prefix}. API calls may fail.")
        else:
            logging.info(f"Successfully loaded {len(loaded_keys)} API key(s) for {env_prefix}.")
        return loaded_keys

    def get_twelve_data_api_key(self) -> Optional[str]:
        """Provides a valid, non-limited Twelve Data API key."""
        # ... (logic remains the same as previous update) ...
        pass

    def mark_key_as_limited(self, key: str, duration: int = 60):
        # ... (logic remains the same) ...
        pass

key_manager_instance = KeyManager()

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), before_sleep=before_sleep_log(RETRY_LOG, logging.WARNING))
async def fetch_twelve_data_ohlc(symbol: str, timeframe: str, output_size: int) -> Optional[List[Dict]]:
    """Fetches OHLC data from Twelve Data API with retry logic."""
    # ... (logic remains the same as previous update) ...
    pass

def get_available_pairs() -> List[str]:
    """Returns a list of trading pairs to be processed."""
    # This can be expanded to read from a config file or database
    return ["EUR/USD", "XAU/USD", "GBP/USD", "BTC/USD"]
    
