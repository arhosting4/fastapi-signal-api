# filename: key_manager.py

import os
import time
import logging
from typing import List, Dict, Optional
from collections import deque
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# ==============================================================================
# ★★★ حتمی ورژن: 5+4 کی پولز اور اسمارٹ ایکسپائری کے ساتھ ★★★
# ==============================================================================

class KeyManager:
    def __init__(self):
        self.guardian_keys: deque[str] = deque()
        self.hunter_keys: deque[str] = deque()
        self.limited_keys: Dict[str, float] = {}
        self.load_and_distribute_keys()

    def load_and_distribute_keys(self):
        """
        ماحولیاتی متغیرات سے تمام کیز کو لوڈ کرتا ہے اور انہیں دو پولز میں تقسیم کرتا ہے۔
        """
        all_keys = []
        keys_str = os.getenv("TWELVE_DATA_API_KEYS", "")
        if keys_str:
            all_keys.extend(key.strip() for key in keys_str.split(',') if key.strip())

        i = 1
        while True:
            key = os.getenv(f"TWELVE_DATA_API_KEY_{i}")
            if not key:
                break
            all_keys.append(key.strip())
            i += 1
        
        unique_keys = sorted(list(set(all_keys)))
        
        if len(unique_keys) < 9:
            logger.error(f"سسٹم کو 9 منفرد API کیز کی ضرورت ہے، لیکن صرف {len(unique_keys)} ملیں۔ براہ کرم مزید کیز شامل کریں۔")
            # اگر کیز کم ہیں تو بھی سسٹم کو چلانے کی کوشش کریں
            guardian_pool_size = min(5, len(unique_keys) - 4) if len(unique_keys) > 4 else len(unique_keys)
        else:
            guardian_pool_size = 5

        self.guardian_keys = deque(unique_keys[:guardian_pool_size])
        self.hunter_keys = deque(unique_keys[guardian_pool_size:])

        logger.info(f"KeyManager شروع کیا گیا: کل {len(unique_keys)} منفرد کیز ملیں۔")
        logger.info(f"🛡️ گارڈین (نگرانی) پول: {len(self.guardian_keys)} کیز۔")
        logger.info(f"🏹 ہنٹر (تلاش) پول: {len(self.hunter_keys)} کیز۔")

    def _get_key_from_pool(self, pool: deque[str]) -> Optional[str]:
        """
        کسی مخصوص پول سے ایک دستیاب API کلید راؤنڈ روبن طریقے سے فراہم کرتا ہے۔
        """
        if not pool:
            return None

        for _ in range(len(pool)):
            key = pool[0]
            pool.rotate(-1)

            if key in self.limited_keys:
                if time.time() > self.limited_keys[key]:
                    del self.limited_keys[key]
                    logger.info(f"کلید {key[:8]}... کی پابندی ختم ہو گئی۔ اسے دوبارہ دستیاب کیا جا رہا ہے۔")
                    return key
                else:
                    continue
            else:
                return key
        
        return None

    def get_guardian_key(self) -> Optional[str]:
        """گارڈین پول سے ایک کلید حاصل کرتا ہے۔"""
        key = self._get_key_from_pool(self.guardian_keys)
        if not key:
            logger.warning("🛡️ گارڈین پول کی تمام کیز فی الحال محدود ہیں۔")
        return key

    def get_hunter_key(self) -> Optional[str]:
        """ہنٹر پول سے ایک کلید حاصل کرتا ہے۔"""
        key = self._get_key_from_pool(self.hunter_keys)
        if not key:
            logger.warning("🏹 ہنٹر پول کی تمام کیز فی الحال محدود ہیں۔")
        return key

    def report_key_issue(self, key: str, is_daily_limit: bool):
        """
        ایک کلید کو اس کی خرابی کی بنیاد پر محدود کے طور پر نشان زد کرتا ہے۔
        """
        if key in self.limited_keys:
            return

        if is_daily_limit:
            now_utc = datetime.now(timezone.utc)
            tomorrow_utc = now_utc + timedelta(days=1)
            midnight_utc = tomorrow_utc.replace(hour=0, minute=0, second=1, microsecond=0)
            expiry_timestamp = midnight_utc.timestamp()
            self.limited_keys[key] = expiry_timestamp
            logger.warning(f"کلید {key[:8]}... کی یومیہ حد ختم! اسے اگلے دن UTC کے آغاز تک محدود کیا جا رہا ہے۔")
        else:
            duration_seconds = 65
            expiry_time = time.time() + duration_seconds
            self.limited_keys[key] = expiry_time

# سنگلٹن مثال
key_manager = KeyManager()
    
