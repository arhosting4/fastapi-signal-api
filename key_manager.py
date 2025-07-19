# key_manager.py

import os
import time
from typing import List, Optional, Dict

# --- اہم تبدیلی: عالمی مثال (global instance) کو ہٹا دیا گیا ہے ---
# ہم اب key_manager کو یہاں نہیں بنائیں گے۔

class KeyManager:
    """
    ماحول کے متغیرات سے متعدد API کلیدوں کو منظم کرتا ہے،
    اور شرح کی حد تک پہنچنے پر خود بخود گردش کرتا ہے۔
    """
    def __init__(self):
        self.keys: List[str] = []
        self.limited_keys: Dict[str, float] = {}
        self.load_keys()

    def load_keys(self):
        """
        TWELVE_DATA_API_KEYS ماحول کے متغیر سے کوما سے الگ کی گئی کلیدوں کو لوڈ کرتا ہے۔
        """
        api_keys_str = os.getenv("TWELVE_DATA_API_KEYS", "")
        self.keys = [key.strip() for key in api_keys_str.split(',') if key.strip()]
        # --- اہم تبدیلی: پرنٹ پیغام کو بہتر بنایا گیا ---
        if not hasattr(self, '_printed_key_count'):
            print(f"--- KeyManager: Found {len(self.keys)} API keys. ---")
            self._printed_key_count = True

    def get_api_key(self) -> Optional[str]:
        """
        ایک دستیاب API کلید واپس کرتا ہے۔
        """
        current_time = time.time()
        for key in self.keys:
            if key not in self.limited_keys or current_time - self.limited_keys.get(key, 0) > 60:
                if key in self.limited_keys:
                    del self.limited_keys[key]
                return key
        
        print("--- KeyManager WARNING: All keys are currently rate-limited. ---")
        return None

    def mark_key_as_limited(self, key: str):
        """
        استعمال شدہ کلید کو عارضی طور پر محدود کے طور پر نشان زد کرتا ہے۔
        """
        if key in self.keys:
            print(f"--- KeyManager INFO: API key limit reached for key ending in ...{key[-4:]}. Rotating. ---")
            self.limited_keys[key] = time.time()

