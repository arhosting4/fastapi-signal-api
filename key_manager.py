# filename: key_manager.py

import os
import time
import logging
from typing import List, Optional, Dict
from collections import deque # ★★★ deque کو امپورٹ کریں گے ★★★

logger = logging.getLogger(__name__)

class KeyManager:
    def __init__(self):
        # ★★★ اب ہم ایک deque استعمال کریں گے جو گھومنے کے لیے بہترین ہے ★★★
        self.keys: deque[str] = deque()
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
        
        # ★★★ فہرست کو deque میں تبدیل کریں ★★★
        self.keys = deque(list(found_keys))
        if not self.keys:
            logger.error("کوئی بھی Twelve Data API کلید لوڈ نہیں ہوئی۔")
        else:
            logger.info(f"KeyManager شروع کیا گیا: {len(self.keys)} منفرد API کلیدیں ملیں۔")

    # ==============================================================================
    # ★★★ نیا اور بہتر، حقیقی راؤنڈ روبن والا get_api_key فنکشن ★★★
    # ==============================================================================
    def get_api_key(self) -> Optional[str]:
        """
        ایک دستیاب API کلید راؤنڈ روبن طریقے سے فراہم کرتا ہے۔
        یہ محدود کیز کو بھی چیک کرتا ہے کہ آیا ان کی پابندی کا وقت ختم ہو گیا ہے۔
        """
        current_time = time.time()
        
        # پہلے محدود کیز کو صاف کریں جن کا وقت ختم ہو گیا ہے
        for key, expiry_time in list(self.limited_keys.items()):
            if current_time > expiry_time:
                del self.limited_keys[key]
                logger.info(f"API کلید {key[:8]}... کی پابندی ختم ہو گئی۔ اسے دوبارہ دستیاب کیا جا رہا ہے۔")

        if not self.keys:
            logger.error("کوئی API کلید دستیاب نہیں ہے۔")
            return None

        # تمام کیز کو چیک کرنے کے لیے ایک چکر لگائیں
        for _ in range(len(self.keys)):
            key = self.keys[0] # پہلی کلید حاصل کریں
            self.keys.rotate(-1) # ★★★ کلیدوں کو گھمائیں تاکہ اگلی بار دوسری کلید آئے ★★★

            if key not in self.limited_keys:
                logger.info(f"راؤنڈ روبن: کلید {key[:8]}... فراہم کی گئی۔")
                return key
        
        logger.warning(f"تمام {len(self.keys)} API کیز فی الحال محدود ہیں۔")
        if self.limited_keys:
            next_available_time = min(self.limited_keys.values())
            wait_seconds = next_available_time - current_time
            logger.info(f"اگلی کلید تقریباً {wait_seconds:.1f} سیکنڈ میں دستیاب ہوگی۔")
            
        return None

    def mark_key_as_limited(self, key: str, duration_seconds: int = 60):
        """
        ایک کلید کو مخصوص مدت کے لیے محدود کے طور پر نشان زد کرتا ہے۔
        """
        if key in self.limited_keys: # اگر پہلے سے محدود ہے تو کچھ نہ کریں
            return
            
        expiry_time = time.time() + duration_seconds
        self.limited_keys[key] = expiry_time
        logger.warning(f"API کلید {key[:8]}... کو {duration_seconds} سیکنڈ کے لیے محدود کر دیا گیا ہے۔")

# سنگلٹن مثال
key_manager = KeyManager()
