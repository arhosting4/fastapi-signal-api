# key_manager.py

import os
import time
from typing import List, Optional, Dict

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
        print(f"KeyManager: Found {len(self.keys)} API keys.")

    def get_api_key(self) -> Optional[str]:
        """
        ایک دستیاب API کلید واپس کرتا ہے جو فی الحال شرح کی حد میں نہیں ہے۔
        اگر کوئی کلید 60 سیکنڈ سے زیادہ کے لیے محدود ہو تو اسے دوبارہ قابل استعمال سمجھا جاتا ہے۔
        """
        current_time = time.time()
        for key in self.keys:
            # اگر کلید محدود نہیں ہے، یا اگر اسے محدود ہوئے 60 سیکنڈ سے زیادہ ہو گئے ہیں
            if key not in self.limited_keys or current_time - self.limited_keys.get(key, 0) > 60:
                # اگر یہ محدود فہرست میں تھی تو اسے ہٹا دیں
                if key in self.limited_keys:
                    del self.limited_keys[key]
                return key
        
        print("--- KeyManager WARNING: All keys are currently rate-limited. Waiting for one to become available. ---")
        return None

    def mark_key_as_limited(self, key: str):
        """
        استعمال شدہ کلید کو عارضی طور پر محدود کے طور پر نشان زد کرتا ہے۔
        """
        if key in self.keys:
            print(f"--- KeyManager INFO: API key limit reached for key ending in ...{key[-4:]}. Rotating. ---")
            self.limited_keys[key] = time.time()

# ایک عالمی مثال بنائیں تاکہ پوری ایپ اسے استعمال کر سکے
key_manager = KeyManager()
