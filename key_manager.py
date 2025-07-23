# filename: key_manager.py

import os
import time
from typing import List, Optional, Dict

class KeyManager:
    def __init__(self):
        self.keys: List[str] = []
        self.limited_keys: Dict[str, float] = {}
        # --- اہم تبدیلی: کیز لوڈ کرنے کے لیے نئے، بہتر فنکشن کو کال کریں ---
        self.load_keys_robustly()

    def load_keys_robustly(self):
        """
        ماحولیاتی متغیرات سے API کیز کو زیادہ مضبوط اور لچکدار طریقے سے لوڈ کرتا ہے۔
        یہ 'TWELVE_DATA_API_KEYS' (کوما سے الگ) اور 'TWELVE_DATA_API_KEY_1', '..._2'
        جیسے متعدد متغیرات کو بھی سپورٹ کرتا ہے۔
        """
        found_keys = set()  # ڈپلیکیٹ کیز سے بچنے کے لیے سیٹ کا استعمال

        # طریقہ 1: کوما سے الگ کی گئی کیز والے واحد متغیر کو چیک کریں
        keys_from_main_var = os.getenv("TWELVE_DATA_API_KEYS", "")
        if keys_from_main_var:
            for key in keys_from_main_var.split(','):
                stripped_key = key.strip()
                if stripped_key:
                    found_keys.add(stripped_key)

        # طریقہ 2: انفرادی متغیرات (TWELVE_DATA_API_KEY_1, _2, ...) کو چیک کریں
        i = 1
        while True:
            individual_key = os.getenv(f"TWELVE_DATA_API_KEY_{i}")
            if individual_key:
                stripped_key = individual_key.strip()
                if stripped_key:
                    found_keys.add(stripped_key)
                i += 1
            else:
                break

        self.keys = list(found_keys)

        if not hasattr(self, '_printed_key_count'):
            print(f"--- KeyManager Initialized: Found {len(self.keys)} unique API key(s) robustly. ---")
            self._printed_key_count = True

    def get_api_key(self) -> Optional[str]:
        """
        ایک دستیاب API کی فراہم کرتا ہے جو حال ہی میں محدود نہ ہوئی ہو۔
        """
        current_time = time.time()
        for key in self.keys:
            if key not in self.limited_keys or current_time - self.limited_keys.get(key, 0) > 60:
                if key in self.limited_keys:
                    del self.limited_keys[key]
                return key

        print("--- KeyManager WARNING: All API keys are currently rate-limited. ---")
        return None

    def mark_key_as_limited(self, key: str):
        """
        ایک کی کو عارضی طور پر محدود کے طور پر نشان زد کرتا ہے۔
        """
        if key in self.keys:
            print(f"--- KeyManager INFO: API key limit reached for key ending in ...{key[-4:]}. Rotating. ---")
            self.limited_keys[key] = time.time()
