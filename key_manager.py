# filename: key_manager.py
import os
import time
import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

class KeyManager:
    def __init__(self):
        self.keys: List[str] = []
        # ★★★ اب یہ ڈکشنری کلید کے ساتھ اس کی پابندی ختم ہونے کا وقت (timestamp) محفوظ کرے گی ★★★
        self.limited_keys: Dict[str, float] = {}
        self.load_keys_robustly()

    def load_keys_robustly(self):
        """
        ماحولیاتی متغیرات سے API کیز کو زیادہ مضبوط اور لچکدار طریقے سے لوڈ کرتا ہے۔
        """
        found_keys = set()
        keys_from_main_var = os.getenv("TWELVE_DATA_API_KEYS", "")
        if keys_from_main_var:
            for key in keys_from_main_var.split(','):
                stripped_key = key.strip()
                if stripped_key:
                    found_keys.add(stripped_key)

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
        if not self.keys:
            logger.error("کوئی بھی Twelve Data API کلید لوڈ نہیں ہوئی۔ براہ کرم TWELVE_DATA_API_KEYS ماحول کا متغیر سیٹ کریں۔")
        else:
            logger.info(f"KeyManager شروع کیا گیا: {len(self.keys)} منفرد API کلیدیں ملیں۔")

    def get_api_key(self) -> Optional[str]:
        """
        ایک دستیاب API کلید فراہم کرتا ہے جو محدود نہ ہو۔
        یہ محدود کیز کو بھی چیک کرتا ہے کہ آیا ان کی پابندی کا وقت ختم ہو گیا ہے۔
        """
        current_time = time.time()
        
        # پہلے محدود کیز کو صاف کریں جن کا وقت ختم ہو گیا ہے
        # نوٹ: یہ ایک کاپی پر iterate کرتا ہے تاکہ ڈکشنری کو دوران iteration تبدیل کیا جا سکے
        for key, expiry_time in list(self.limited_keys.items()):
            if current_time > expiry_time:
                del self.limited_keys[key]
                logger.info(f"API کلید {key[:8]}... کی پابندی ختم ہو گئی۔ اسے دوبارہ دستیاب کیا جا رہا ہے۔")

        # اب ایک دستیاب کلید تلاش کریں
        for key in self.keys:
            if key not in self.limited_keys:
                return key
        
        logger.warning(f"تمام {len(self.keys)} API کیز فی الحال محدود ہیں۔")
        # سب سے جلد دستیاب ہونے والی کلید کا انتظار کا وقت بتائیں
        if self.limited_keys:
            next_available_time = min(self.limited_keys.values())
            wait_seconds = next_available_time - current_time
            logger.info(f"اگلی کلید تقریباً {wait_seconds:.1f} سیکنڈ میں دستیاب ہوگی۔")
            
        return None

    def mark_key_as_limited(self, key: str, duration_seconds: int = 60):
        """
        ایک کلید کو مخصوص مدت کے لیے محدود کے طور پر نشان زد کرتا ہے۔
        """
        if key in self.keys:
            expiry_time = time.time() + duration_seconds
            self.limited_keys[key] = expiry_time
            logger.warning(f"API کلید {key[:8]}... کو {duration_seconds} سیکنڈ کے لیے محدود کر دیا گیا ہے۔")

# سنگلٹن مثال
key_manager = KeyManager()
