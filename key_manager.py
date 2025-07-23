import os
import time
import logging
from typing import List, Optional, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class KeyManager:
    """
    Manages API keys for external services like Twelve Data.
    Handles loading keys from environment variables, rotating keys to avoid rate limits,
    and marking keys as temporarily limited.
    This is the single source of truth for API key management in the project.
    """
    def __init__(self):
        self.twelve_data_keys: List[str] = []
        self.limited_keys: Dict[str, float] = {}  # key -> expiry_timestamp
        self.current_key_index: int = 0
        self._load_twelve_data_keys()

    def _load_twelve_data_keys(self):
        """
        Loads Twelve Data API keys from environment variables.
        Supports both a comma-separated list and individual numbered keys for flexibility.
        """
        keys = set()
        
        # Method 1: Load from a comma-separated string
        keys_from_env = os.getenv("TWELVE_DATA_API_KEYS")
        if keys_from_env:
            keys.update([key.strip() for key in keys_from_env.split(',') if key.strip()])

        # Method 2: Load from individually numbered environment variables (e.g., TWELVE_DATA_API_KEY_1)
        i = 1
        while True:
            key = os.getenv(f"TWELVE_DATA_API_KEY_{i}")
            if key:
                keys.add(key.strip())
                i += 1
            else:
                break
        
        self.twelve_data_keys = list(keys)
        if not self.twelve_data_keys:
            logging.warning("No Twelve Data API keys found in environment variables. API calls will fail.")
        else:
            logging.info(f"Successfully loaded {len(self.twelve_data_keys)} Twelve Data API key(s).")

    def get_twelve_data_api_key(self) -> Optional[str]:
        """
        Provides a valid, non-limited Twelve Data API key using a round-robin approach.
        Skips keys that are temporarily marked as limited.
        """
        if not self.twelve_data_keys:
            return None

        # Clean up expired limited keys
        current_time = time.time()
        self.limited_keys = {key: exp_time for key, exp_time in self.limited_keys.items() if current_time < exp_time}

        # Find a valid key, trying each key at most once
        for _ in range(len(self.twelve_data_keys)):
            key = self.twelve_data_keys[self.current_key_index]
            self.current_key_index = (self.current_key_index + 1) % len(self.twelve_data_keys)
            
            if key not in self.limited_keys:
                return key
        
        logging.warning("All Twelve Data API keys are currently rate-limited.")
        return None

    def mark_key_as_limited(self, key: str, limit_duration_seconds: int = 60):
        """
        Marks a specific API key as rate-limited for a given duration.
        """
        if key in self.twelve_data_keys:
            expiry_time = time.time() + limit_duration_seconds
            self.limited_keys[key] = expiry_time
            logging.warning(f"API key ending with '...{key[-4:]}' has been rate-limited for {limit_duration_seconds} seconds.")

# To be used as a singleton instance across the application
key_manager_instance = KeyManager()
