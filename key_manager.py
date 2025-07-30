# filename: key_manager.py

import os
import time
import logging
from typing import List, Optional, Dict, Deque
from collections import deque
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# ==============================================================================
# ★★★ نیا منصوبہ: گلوبل راؤنڈ روبن ★★★
# تمام کیز ایک ہی پول میں ہیں اور باری باری استعمال ہوتی ہیں۔
# ==============================================================================

class KeyManager:
    def __init__(self):
        self.keys: Deque[str] = deque(self._load_all_keys())
        self.limited_keys: Dict[str, float] = {}
        logger.info(f"🔑 گلوبل راؤنڈ روبن KeyManager شروع کیا گیا۔ کل دستیاب کیز: {len(self.keys)}")

    def _load_all_keys(self) -> List[str]:
        """تمام ماحولیاتی متغیرات سے API کیز کو لوڈ اور ترتیب دیتا ہے۔"""
        found_keys = set()
        env_keys = os.getenv("TWELVE_DATA_API_KEYS")
        if env_keys:
            found_keys.update(key.strip() for key in env_keys.split(',') if key.strip())
        i = 1
        while True:
            key = os.getenv(f"TWELVE_DATA_API_KEY_{i}")
            if not key: break
            found_keys.add(key.strip())
            i += 1
        return sorted(list(found_keys))

    def get_api_key(self) -> Optional[str]:
        """ایک دستیاب API کلید راؤنڈ روبن طریقے سے فراہم کرتا ہے۔"""
        current_time = time.time()
        
        # محدود کیز کو صاف کریں جن کا وقت ختم ہو گیا ہے
        # ہم ایک چکر میں صرف ایک کلید کو صاف کریں گے تاکہ زیادہ وقت نہ لگے۔
        if self.limited_keys:
            key, expiry_time = next(iter(self.limited_keys.items()))
            if current_time > expiry_time:
                del self.limited_keys[key]
                self.keys.append(key)
                logger.info(f"✅ کلید {key[:8]}... کی پابندی ختم۔ یہ اب دستیاب ہے۔")

        if not self.keys:
            logger.error("❌ پول میں کوئی بھی کلید دستیاب نہیں۔ تمام کیز محدود ہیں۔")
            return None

        # اگلی دستیاب کلید حاصل کریں اور اسے قطار کے آخر میں بھیج دیں
        key_to_use = self.keys.popleft()
        self.keys.append(key_to_use)
        
        logger.info(f"👍 کلید {key_to_use[:8]}... فراہم کی گئی۔ پول میں باقی دستیاب کیز: {len(self.keys)}")
        return key_to_use

    def mark_key_as_limited(self, key: str, daily_limit_exceeded: bool = False):
        """ایک کلید کو محدود کے طور پر نشان زد کرتا ہے۔"""
        if key in self.limited_keys: return
        
        # کلید کو فعال قطار سے ہٹا دیں
        if key in self.keys:
            self.keys.remove(key)

        if daily_limit_exceeded:
            now_utc = datetime.now(timezone.utc)
            tomorrow_utc = now_utc + timedelta(days=1)
            expiry_time = tomorrow_utc.replace(hour=0, minute=0, second=1, microsecond=0).timestamp()
            logger.warning(f"🚫 روزانہ کی حد ختم! کلید {key[:8]}... کو اگلے دن تک محدود کیا جا رہا ہے۔")
        else:
            expiry_time = time.time() + 60
            logger.warning(f"⏳ عارضی پابندی! کلید {key[:8]}... کو 60 سیکنڈ کے لیے محدود کیا گیا۔")
            
        self.limited_keys[key] = expiry_time

# سنگلٹن مثال
key_manager = KeyManager()
            
