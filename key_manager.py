# filename: key_manager.py

import os
import time
import logging
from typing import List, Optional, Dict, Deque
from collections import deque
from datetime import datetime, timedelta, timezone # ★★★ نیا امپورٹ ★★★

logger = logging.getLogger(__name__)

# ==============================================================================
# ★★★ حتمی ورژن 2.0: ذہین محدود کرنے کی منطق کے ساتھ ★★★
# یہ کیز کو اگلے دن UTC 00:00 بجے تک محدود کرتا ہے۔
# ==============================================================================

class KeyPool:
    """
    API کیز کے ایک مخصوص پول کو منظم کرنے کے لیے ایک کلاس۔
    یہ ایک ٹیم کی طرح کام کرتا ہے جسے مخصوص کام کے لیے کیز دی گئی ہیں۔
    """
    def __init__(self, pool_name: str, keys: List[str]):
        self.pool_name = pool_name
        self.keys: Deque[str] = deque(keys)
        self.limited_keys: Dict[str, float] = {}
        if keys:
            logger.info(f"🔑 [{self.pool_name}] پول {len(keys)} کیز کے ساتھ شروع کیا گیا۔ پہلی کلید: {keys[0][:8]}...")
        else:
            logger.warning(f"🔑 [{self.pool_name}] پول کو کوئی کلید فراہم نہیں کی گئی۔")

    def get_api_key(self) -> Optional[str]:
        """اس پول سے ایک دستیاب API کلید فراہم کرتا ہے۔"""
        current_time = time.time()
        
        # محدود کیز کو صاف کریں جن کا وقت ختم ہو گیا ہے
        for key, expiry_time in list(self.limited_keys.items()):
            if current_time > expiry_time:
                del self.limited_keys[key]
                self.keys.append(key) # کلید کو واپس پول میں شامل کریں
                logger.info(f"✅ [{self.pool_name}] کلید {key[:8]}... کی پابندی ختم۔ یہ اب دستیاب ہے۔")

        if not self.keys:
            logger.warning(f"[{self.pool_name}] پول میں کوئی دستیاب کلید نہیں۔")
            return None

        # ایک چکر میں دستیاب کلید تلاش کریں
        for _ in range(len(self.keys)):
            key = self.keys[0]
            self.keys.rotate(-1) # کلید کو قطار کے آخر میں بھیج دیں

            if key not in self.limited_keys:
                logger.info(f"👍 [{self.pool_name}] پول سے کلید {key[:8]}... فراہم کی گئی۔")
                return key
        
        logger.error(f"❌ [{self.pool_name}] پول کی تمام کیز فی الحال محدود ہیں۔")
        return None

    def mark_key_as_limited(self, key: str, daily_limit_exceeded: bool = False):
        """
        ایک کلید کو محدود کے طور پر نشان زد کرتا ہے۔
        ★★★ اب یہ اگلے دن UTC 00:00 بجے تک محدود کرتا ہے۔ ★★★
        """
        if key in self.limited_keys:
            return
        
        if daily_limit_exceeded:
            # اگلے دن UTC 00:00 کا وقت حاصل کریں
            now_utc = datetime.now(timezone.utc)
            tomorrow_utc = now_utc + timedelta(days=1)
            next_midnight_utc = tomorrow_utc.replace(hour=0, minute=0, second=1, microsecond=0)
            
            expiry_time = next_midnight_utc.timestamp()
            wait_hours = (expiry_time - now_utc.timestamp()) / 3600
            
            logger.warning(f"🚫 [{self.pool_name}] روزانہ کی حد ختم! کلید {key[:8]}... کو اگلے دن تک محدود کیا جا رہا ہے ({wait_hours:.1f} گھنٹے)۔")
        else:
            # عارضی خرابی کے لیے 60 سیکنڈ کی پابندی
            expiry_time = time.time() + 60
            logger.warning(f"⏳ [{self.pool_name}] کلید {key[:8]}... کو 60 سیکنڈ کے لیے عارضی طور پر محدود کیا گیا۔")
            
        self.limited_keys[key] = expiry_time


class MultiPoolKeyManager:
    """
    مختلف کاموں کے لیے API کیز کے متعدد پولز کا انتظام کرتا ہے۔
    یہ ہمارے "اسمارٹ ٹرائیڈنٹ" منصوبے کی بنیاد ہے۔
    """
    def __init__(self):
        all_keys = self._load_all_keys()
        
        if len(all_keys) >= 9:
            logger.info("ٹرائیڈنٹ حکمت عملی فعال: 9+ کیز ملیں۔ کیز کو 3 پولز میں تقسیم کیا جا رہا ہے۔")
            self.scanner_pool = KeyPool("Scanner", all_keys[0:2])
            self.analysis_pool = KeyPool("Analysis", all_keys[2:7])
            self.monitoring_pool = KeyPool("Monitoring", all_keys[7:9])
        else:
            logger.warning(f"صرف {len(all_keys)} کیز ملیں۔ ٹرائیڈنٹ حکمت عملی کے لیے 9 کیز درکار ہیں۔ فال بیک موڈ فعال۔")
            single_pool = KeyPool("Default", all_keys)
            self.scanner_pool = single_pool
            self.analysis_pool = single_pool
            self.monitoring_pool = single_pool

    def _load_all_keys(self) -> List[str]:
        """تمام ماحولیاتی متغیرات سے API کیز کو لوڈ اور ترتیب دیتا ہے۔"""
        found_keys = set()
        
        env_keys = os.getenv("TWELVE_DATA_API_KEYS")
        if env_keys:
            found_keys.update(key.strip() for key in env_keys.split(',') if key.strip())

        i = 1
        while True:
            key = os.getenv(f"TWELVE_DATA_API_KEY_{i}")
            if not key:
                break
            found_keys.add(key.strip())
            i += 1
        
        key_list = sorted(list(found_keys))
        logger.info(f"KeyManager نے کل {len(key_list)} منفرد API کیز لوڈ کی ہیں۔")
        return key_list

# ==============================================================================
# سنگلٹن مثال: پورے پروجیکٹ میں اسی ایک آبجیکٹ کو استعمال کیا جائے گا۔
# ==============================================================================
key_manager = MultiPoolKeyManager()
    
