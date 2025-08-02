# filename: key_manager.py

import logging
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

# مقامی امپورٹس
from config import api_settings

logger = logging.getLogger(__name__)

class KeyManager:
    """
    API کیز کو ایک مرکزی پول میں منظم کرتا ہے اور شرح کی حدود (rate limits) کو سنبھالتا ہے۔
    یہ ورژن اصل ڈیزائن کی سادگی اور مضبوطی پر مبنی ہے۔
    """
    def __init__(self):
        # تمام کیز کے لیے ایک ہی پول
        self.keys: deque[str] = deque()
        # محدود کیز اور ان کی پابندی کے خاتمے کا وقت
        self.limited_keys: Dict[str, float] = {}
        self._load_keys()

    def _load_keys(self):
        """
        ماحولیاتی متغیرات سے تمام کیز کو لوڈ کرتا ہے۔
        """
        # config.py سے کیز کی فہرست حاصل کریں
        all_keys = api_settings.twelve_data_keys_list
        unique_keys = sorted(list(set(all_keys)))
        
        if not unique_keys:
            logger.critical("کوئی بھی Twelve Data API کلید فراہم نہیں کی گئی۔ سسٹم کام نہیں کر سکتا۔")
            return

        self.keys = deque(unique_keys)
        logger.info(f"KeyManager شروع کیا گیا: کل {len(self.keys)} منفرد کیز کامیابی سے لوڈ ہو گئیں۔")

    def get_key(self) -> Optional[str]:
        """
        پول سے ایک دستیاب API کلید راؤنڈ روبن طریقے سے فراہم کرتا ہے۔
        """
        if not self.keys:
            logger.error("استعمال کے لیے کوئی API کیز دستیاب نہیں ہیں۔")
            return None

        # پول میں موجود تمام کیز کو ایک بار چیک کریں
        for _ in range(len(self.keys)):
            # قطار میں سب سے پہلی کلید حاصل کریں
            key = self.keys[0]
            # اسے قطار کے آخر میں بھیج دیں تاکہ اگلی بار دوسری کلید استعمال ہو
            self.keys.rotate(-1)

            # چیک کریں کہ آیا یہ کلید محدود ہے
            if key in self.limited_keys:
                # اگر پابندی کا وقت ختم ہو گیا ہے تو اسے دوبارہ فعال کریں
                if time.time() > self.limited_keys[key]:
                    del self.limited_keys[key]
                    logger.info(f"کلید {key[:8]}... کی پابندی ختم ہو گئی۔ اسے دوبارہ دستیاب کیا جا رہا ہے۔")
                    return key # کلید اب دستیاب ہے
                else:
                    # یہ کلید ابھی بھی محدود ہے، اگلی چیک کریں
                    continue
            else:
                # یہ کلید محدود نہیں ہے، اسے استعمال کریں
                return key
        
        # اگر لوپ مکمل ہو جائے اور کوئی بھی کلید دستیاب نہ ہو
        logger.warning("تمام API کیز فی الحال عارضی طور پر محدود ہیں۔")
        return None

    def report_key_issue(self, key: str, is_daily_limit: bool):
        """
        ایک کلید کو اس کی خرابی کی بنیاد پر محدود کے طور پر نشان زد کرتا ہے۔
        """
        if key in self.limited_keys:
            return # یہ کلید پہلے ہی محدود ہے

        if is_daily_limit:
            # اگر یومیہ حد ختم ہوئی ہے، تو اگلے دن UTC آدھی رات تک محدود کریں
            now_utc = datetime.now(timezone.utc)
            tomorrow_utc = now_utc + timedelta(days=1)
            midnight_utc = tomorrow_utc.replace(hour=0, minute=0, second=1, microsecond=0)
            expiry_timestamp = midnight_utc.timestamp()
            self.limited_keys[key] = expiry_timestamp
            logger.warning(f"کلید {key[:8]}... کی یومیہ حد ختم! اسے اگلے دن UTC کے آغاز تک محدود کیا جا رہا ہے۔")
        else:
            # اگر فی منٹ کی حد ختم ہوئی ہے، تو 65 سیکنڈ کے لیے محدود کریں
            duration_seconds = 65
            expiry_time = time.time() + duration_seconds
            self.limited_keys[key] = expiry_time
            expiry_dt = datetime.fromtimestamp(expiry_time)
            logger.warning(f"کلید {key[:8]}... کی فی منٹ حد ختم! اسے {duration_seconds} سیکنڈ ({expiry_dt.isoformat()}) کے لیے محدود کیا جا رہا ہے۔")

# سنگلٹن مثال تاکہ پوری ایپلیکیشن میں ایک ہی مینیجر استعمال ہو
key_manager = KeyManager()
            
