# filename: key_manager.py
import os
import time
import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

class KeyManager:
    def __init__(self):
        self.keys: List[str] = []
        self.limited_keys: Dict[str, float] = {}
        self.load_keys_robustly()

    def load_keys_robustly(self):
        """
        ماحولیاتی متغیرات سے API کیز کو زیادہ مضبوط اور لچکدار طریقے سے لوڈ کرتا ہے۔
        """
        found_keys = set()

        # طریقہ 1: کوما سے الگ کی گئی کیز
        keys_from_main_var = os.getenv("TWELVE_DATA_API_KEYS", "")
        if keys_from_main_var:
            for key in keys_from_main_var.split(','):
                stripped_key = key.strip()
                if stripped_key:
                    found_keys.add(stripped_key)

        # طریقہ 2: انفرادی متغیرات
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
        logger.info(f"KeyManager شروع کیا گیا: {len(self.keys)} منفرد API کلیدیں ملیں۔")

    def get_api_key(self) -> Optional[str]:
        """ایک دستیاب API کلید فراہم کرتا ہے۔"""
        current_time = time.time()
        for key in self.keys:
            if key not in self.limited_keys or current_time - self.limited_keys.get(key, 0) > 60:
                if key in self.limited_keys:
                    del self.limited_keys[key]
                return key
        
        logger.warning("تمام API کیز فی الحال شرح کی حد میں ہیں۔")
        return None

    def mark_key_as_limited(self, key: str):
        """ایک کلید کو عارضی طور پر محدود کے طور پر نشان زد کرتا ہے۔"""
        if key in self.keys:
            self.limited_keys[key] = time.time()

# سنگلٹن مثال
key_manager = KeyManager()
