# filename: key_manager.py

import logging
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Deque

# مقامی امپورٹس
# مرکزی کنفیگریشن ماڈیول سے سیٹنگز درآمد کریں
from config import api_settings

logger = logging.getLogger(__name__)

class KeyManager:
    """
    API کیز کو منظم کرتا ہے، انہیں پولز میں تقسیم کرتا ہے، اور شرح کی حدود کو سنبھالتا ہے۔
    یہ ایک سنگلٹن کلاس کے طور پر استعمال ہوتی ہے۔
    """
    def __init__(self):
        """
        KeyManager کو شروع کرتا ہے، تمام کیز کو لوڈ کرتا ہے اور انہیں دو مخصوص پولز میں تقسیم کرتا ہے۔
        """
        self.guardian_keys: Deque[str] = deque()
        self.hunter_keys: Deque[str] = deque()
        # محدود کیز اور ان کی پابندی ختم ہونے کا وقت (UNIX ٹائم اسٹیمپ)
        self.limited_keys: Dict[str, float] = {}
        self._load_and_distribute_keys()

    def _load_and_distribute_keys(self):
        """
        کنفیگریشن سے تمام کیز کو لوڈ کرتا ہے اور انہیں گارڈین اور ہنٹر پولز میں تقسیم کرتا ہے۔
        """
        # مرکزی کنفیگریشن سے کیز کی فہرست حاصل کریں
        all_keys = api_settings.twelve_data_keys_list
        
        # ڈپلیکیٹ کیز کو ہٹا کر ایک منفرد اور ترتیب شدہ فہرست بنائیں
        unique_keys = sorted(list(set(all_keys)))
        
        if not unique_keys:
            logger.critical("کوئی Twelve Data API کلید فراہم نہیں کی گئی۔ سسٹم کام نہیں کر سکتا۔")
            # یہاں سسٹم سے باہر نکلنا یا ایک استثناء پھینکنا ایک آپشن ہو سکتا ہے
            return

        if len(unique_keys) < 9:
            logger.warning(f"سسٹم کو 9 منفرد API کیز کی ضرورت ہے، لیکن صرف {len(unique_keys)} ملیں۔ کارکردگی متاثر ہو سکتی ہے۔")
            # اگر کیز کم ہیں تو بھی سسٹم کو چلانے کی کوشش کریں
            guardian_pool_size = min(5, len(unique_keys) - 4) if len(unique_keys) > 4 else len(unique_keys)
        else:
            # تجویز کردہ تقسیم: 5 گارڈین کے لیے، باقی ہنٹر کے لیے
            guardian_pool_size = 5

        self.guardian_keys = deque(unique_keys[:guardian_pool_size])
        self.hunter_keys = deque(unique_keys[guardian_pool_size:])

        logger.info(f"🔑 KeyManager شروع کیا گیا: کل {len(unique_keys)} منفرد کیز ملیں۔")
        logger.info(f"🛡️ گارڈین (نگرانی) پول: {len(self.guardian_keys)} کیز۔")
        logger.info(f"🏹 ہنٹر (تلاش) پول: {len(self.hunter_keys)} کیز۔")

    def _get_key_from_pool(self, pool: Deque[str]) -> Optional[str]:
        """
        کسی مخصوص پول سے ایک دستیاب API کلید راؤنڈ روبن طریقے سے فراہم کرتا ہے۔
        یہ محدود کیز کو بھی چیک کرتا ہے اور اگر ان کی پابندی ختم ہو گئی ہو تو انہیں دوبارہ فعال کرتا ہے۔
        """
        if not pool:
            return None

        # پول میں موجود تمام کیز کو ایک بار چیک کریں
        for _ in range(len(pool)):
            key = pool[0]
            pool.rotate(-1)  # کی کو قطار کے آخر میں بھیج دیں

            if key in self.limited_keys:
                # چیک کریں کہ آیا کی کی پابندی کا وقت ختم ہو گیا ہے
                if time.time() > self.limited_keys[key]:
                    expiry_time = datetime.fromtimestamp(self.limited_keys.pop(key), tz=timezone.utc)
                    logger.info(f"✅ کلید {key[:8]}... کی پابندی ختم ہو گئی۔ اسے دوبارہ دستیاب کیا جا رہا ہے۔ (پابندی ختم ہوئی: {expiry_time.isoformat()})")
                    return key  # کی اب دستیاب ہے
                else:
                    continue  # یہ کی ابھی بھی محدود ہے، اگلی چیک کریں
            else:
                return key  # یہ کی محدود نہیں ہے، اسے استعمال کریں
        
        # اگر لوپ مکمل ہو جائے اور کوئی کی نہ ملے
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
            return  # یہ کی پہلے ہی محدود ہے

        if is_daily_limit:
            # اگر یومیہ حد ختم ہوئی ہے، تو اگلے دن UTC آدھی رات تک محدود کریں
            now_utc = datetime.now(timezone.utc)
            tomorrow_utc = now_utc + timedelta(days=1)
            midnight_utc = tomorrow_utc.replace(hour=0, minute=1, second=0, microsecond=0)
            expiry_timestamp = midnight_utc.timestamp()
            self.limited_keys[key] = expiry_timestamp
            logger.warning(f"🚫 کلید {key[:8]}... کی یومیہ حد ختم! اسے اگلے دن UTC ({midnight_utc.isoformat()}) تک محدود کیا جا رہا ہے۔")
        else:
            # اگر فی منٹ کی حد ختم ہوئی ہے، تو 65 سیکنڈ کے لیے محدود کریں
            duration_seconds = 65
            expiry_time = time.time() + duration_seconds
            self.limited_keys[key] = expiry_time
            expiry_dt = datetime.fromtimestamp(expiry_time, tz=timezone.utc)
            logger.warning(f"⏳ کلید {key[:8]}... کی فی منٹ حد ختم! اسے {duration_seconds} سیکنڈ ({expiry_dt.isoformat()}) کے لیے محدود کیا جا رہا ہے۔")

# سنگلٹن مثال (تاکہ پورے پروجیکٹ میں ایک ہی مینیجر استعمال ہو)
key_manager = KeyManager()
