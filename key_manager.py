import os
import time
from typing import List, Optional, Dict

class KeyManager:
    def __init__(self):
        self.keys: List[str] = []
        self.limited_keys: Dict[str, float] = {}
        self.load_keys()

    def load_keys(self):
        api_keys_str = os.getenv("TWELVE_DATA_API_KEYS", "")
        self.keys = [key.strip() for key in api_keys_str.split(',') if key.strip()]
        if not hasattr(self, '_printed_key_count'):
            print(f"--- KeyManager Class Initialized: Found {len(self.keys)} API keys. ---")
            self._printed_key_count = True

    def get_api_key(self) -> Optional[str]:
        current_time = time.time()
        for key in self.keys:
            if key not in self.limited_keys or current_time - self.limited_keys.get(key, 0) > 60:
                if key in self.limited_keys:
                    del self.limited_keys[key]
                return key
        return None

    def mark_key_as_limited(self, key: str):
        if key in self.keys:
            print(f"--- KeyManager INFO: API key limit reached for key ending in ...{key[-4:]}. Rotating. ---")
            self.limited_keys[key] = time.time()
            
