# filename: key_manager.py

import os
import time
import logging
from typing import List, Optional, Dict
from collections import deque

logger = logging.getLogger(__name__)

# ==============================================================================
# ★★★ حتمی ورژن: طویل مدتی پابندی اور بہتر کلید کے انتظام کے ساتھ ★★★
# ==============================================================================
class KeyManager:
    def __init__(self):
        self.keys: deque[str] = deque()
        self.limited_keys: Dict[str, float] = {}
        self.load_keys_robustly()

    def load_keys_robustly(self):
        """
        ماحولیاتی متغیرات سے API کیز کو زیادہ مضبوط اور لچکدار طریقے سے لوڈ کرتا ہے۔
        """
        found_keys = set(filter(None, os.getenv("TWELVE_DATA_API_KEYS", "").split(',')))
        i = 1
        while True:
            key = os.getenv(f"TWELVE_DATA_API_KEY_{i}")
            if not key: break
            found_keys.add(key.strip())
            i += 1
        
        self.keys = deque(list(found_keys))
        if not self.keys:
            logger.error("کوئی بھی Twelve Data API کلید لوڈ نہیں ہوئی۔")
        else:
            logger.info(f"KeyManager شروع کیا گیا: {len(self.keys)} منفرد API کلیدیں ملیں۔")

    def get_api_key(self) -> Optional[str]:
        """
        ایک دستیاب API کلید راؤنڈ روبن طریقے سے فراہم کرتا ہے۔
        """
        current_time = time.time()
        
        # محدود کیز کو صاف کریں جن کا وقت ختم ہو گیا ہے
        for key, expiry_time in list(self.limited_keys.items()):
            if current_time > expiry_time:
                del self.limited_keys[key]
                logger.info(f"API کلید {key[:8]}... کی پابندی ختم ہو گئی۔ اسے دوبارہ دستیاب کیا جا رہا ہے۔")

        if not self.keys:
            return None

        # تمام کیز کو چیک کرنے کے لیے ایک چکر لگائیں
        for _ in range(len(self.keys)):
            key = self.keys[0]
            self.keys.rotate(-1)

            if key not in self.limited_keys:
                logger.info(f"راؤنڈ روبن: کلید {key[:8]}... فراہم کی گئی۔")
                return key
        
        logger.warning(f"تمام {len(self.keys)} API کیز فی الحال محدود ہیں۔")
        if self.limited_keys:
            next_available_time = min(self.limited_keys.values())
            wait_seconds = next_available_time - current_time
            logger.info(f"اگلی کلید تقریباً {wait_seconds/3600:.1f} گھنٹوں میں دستیاب ہوگی۔")
            
        return None

    def mark_key_as_limited(self, key: str, daily_limit_exceeded: bool = False):
        """
        ایک کلید کو محدود کے طور پر نشان زد کرتا ہے۔
        اگر روزانہ کی حد ختم ہو جائے تو 22 گھنٹے کے لیے محدود کرتا ہے۔
        """
        if key in self.limited_keys:
            return
        
        # ★★★ یہاں نئی منطق ہے ★★★
        if daily_limit_exceeded:
            duration_seconds = 22 * 60 * 60  # 22 گھنٹے
            logger.warning(f"روزانہ کی حد ختم! API کلید {key[:8]}... کو 22 گھنٹے کے لیے محدود کیا جا رہا ہے۔")
        else:
            duration_seconds = 60  # 60 سیکنڈ (عارضی خرابی کے لیے)
            logger.warning(f"API کلید {key[:8]}... کو 60 سیکنڈ کے لیے محدود کیا جا رہا ہے۔")
            
        expiry_time = time.time() + duration_seconds
        self.limited_keys[key] = expiry_time

# سنگلٹن مثال
key_manager = KeyManager()
