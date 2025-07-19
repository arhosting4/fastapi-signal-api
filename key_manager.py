# filename: key_manager.py
import time
from typing import List, Optional

class KeyManager:
    def __init__(self, keys: List[str]):
        if not keys:
            print("--- KeyManager WARNING: No API keys provided. ---")
            self.keys = []
        else:
            self.keys = keys
        self.current_key_index = 0
        self.last_invalidation_time = 0
        print(f"--- KeyManager Class Initialized: Found {len(self.keys)} API keys. ---")

    def get_key(self) -> Optional[str]:
        if not self.keys:
            return None
        
        # اگر موجودہ کی کام کر رہی ہے تو وہی واپس کریں
        return self.keys[self.current_key_index]

    def invalidate_current_key(self):
        # اگر ایک سیکنڈ سے بھی کم وقت میں دوبارہ کال ہو تو نظر انداز کریں
        if time.time() - self.last_invalidation_time < 1:
            return

        print(f"--- KeyManager: Invalidating key at index {self.current_key_index}. ---")
        self.last_invalidation_time = time.time()
        # اگلی کی پر جائیں
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        print(f"--- KeyManager: Switched to new key at index {self.current_key_index}. ---")

