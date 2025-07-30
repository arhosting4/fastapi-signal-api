# filename: key_manager.py

import os
import time
import logging
from typing import List, Optional, Dict
from collections import deque
import threading

logger = logging.getLogger(__name__)

# ==============================================================================
# ★★★ حتمی ورژن: اسٹیٹ فل کی مینیجر (یادداشت کے ساتھ) ★★★
# ==============================================================================
class KeyManager:
    def __init__(self):
        self.keys: List[str] = []
        self.limited_keys: Dict[str, float] = {}
        self.current_index: int = 0
        self.lock = threading.Lock()
        self._load_keys_robustly()

    def _load_keys_robustly(self):
        """ماحولیاتی متغیرات سے API کیز کو زیادہ مضبوط اور لچکدار طریقے سے لوڈ کرتا ہے۔"""
        found_keys = set()
        # بنیادی متغیر سے کیز لوڈ کریں
        env_keys = os.getenv("TWELVE_DATA_API_KEYS", "")
        if env_keys:
            found_keys.update(key.strip() for key in env_keys.split(',') if key.strip())
        
        # انفرادی متغیرات سے کیز لوڈ کریں (e.g., TWELVE_DATA_API_KEY_1, _2, etc.)
        i = 1
        while True:
            key = os.getenv(f"TWELVE_DATA_API_KEY_{i}")
            if not key:
                break
            found_keys.add(key.strip())
            i += 1
        
        self.keys = list(found_keys)
        if not self.keys:
            logger.error("کوئی بھی Twelve Data API کلید لوڈ نہیں ہوئی۔ سسٹم کام نہیں کرے گا۔")
        else:
            logger.info(f"KeyManager شروع کیا گیا: {len(self.keys)} منفرد API کلیدیں ملیں۔")

    def _get_next_available_key(self) -> Optional[str]:
        """گھومنے والے انڈیکس کا استعمال کرتے ہوئے اگلی دستیاب کلید تلاش کرتا ہے۔"""
        if not self.keys:
            return None

        # تمام کیز کو ایک چکر میں چیک کریں
        for _ in range(len(self.keys)):
            key = self.keys[self.current_index]
            
            # انڈیکس کو اگلے چکر کے لیے آگے بڑھائیں
            self.current_index = (self.current_index + 1) % len(self.keys)

            if key not in self.limited_keys:
                logger.info(f"👍 کلید {key[:8]}... فراہم کی گئی۔ اگلا انڈیکس: {self.current_index}")
                return key
        
        # اگر کوئی بھی کلید دستیاب نہیں ہے
        return None

    def get_api_key(self) -> Optional[str]:
        """ایک دستیاب API کلید تھریڈ-سیف طریقے سے فراہم کرتا ہے۔"""
        with self.lock:
            # محدود کیز کو صاف کریں جن کا وقت ختم ہو گیا ہے
            current_time = time.time()
            keys_to_remove = [key for key, expiry_time in self.limited_keys.items() if current_time > expiry_time]
            
            for key in keys_to_remove:
                del self.limited_keys[key]
                logger.info(f"✅ API کلید {key[:8]}... کی پابندی ختم ہو گئی۔ اسے دوبارہ دستیاب کیا جا رہا ہے۔")

            key = self._get_next_available_key()
            if not key:
                logger.warning(f"تمام {len(self.keys)} API کیز فی الحال محدود ہیں۔")
                if self.limited_keys:
                    next_available_time = min(self.limited_keys.values())
                    wait_seconds = next_available_time - current_time
                    logger.info(f"اگلی کلید تقریباً {wait_seconds/3600:.1f} گھنٹوں میں دستیاب ہوگی۔")
            return key

    def mark_key_as_limited(self, key: str, daily_limit_exceeded: bool = False):
        """ایک کلید کو محدود کے طور پر نشان زد کرتا ہے۔"""
        with self.lock:
            if key in self.limited_keys:
                return
            
            if daily_limit_exceeded:
                # اگلے دن UTC آدھی رات تک محدود کریں + 5 منٹ کا بفر
                now = datetime.utcnow()
                midnight = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)
                expiry_time = midnight.timestamp() + (5 * 60) # 5 منٹ کا بفر
                duration_hours = (expiry_time - time.time()) / 3600
                logger.warning(f"🚫 روزانہ کی حد ختم! API کلید {key[:8]}... کو اگلے دن تک ({duration_hours:.1f} گھنٹے) کے لیے محدود کیا جا رہا ہے۔")
            else:
                # منٹ کی حد کے لیے 65 سیکنڈ
                duration_seconds = 65
                expiry_time = time.time() + duration_seconds
                logger.warning(f"⏱️ منٹ کی حد ختم! API کلید {key[:8]}... کو 65 سیکنڈ کے لیے محدود کیا جا رہا ہے۔")
            
            self.limited_keys[key] = expiry_time

# سنگلٹن مثال
key_manager = KeyManager()
            
