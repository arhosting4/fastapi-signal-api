# filename: key_manager.py

import logging
from typing import Dict, Optional, List

from config import api_settings, trading_settings

logger = logging.getLogger(__name__)

class KeyManager:
    """
    API کیز کو منظم کرتا ہے اور ہر ٹریڈنگ جوڑے کو ایک مخصوص کلید تفویض کرتا ہے
    تاکہ API کی فی منٹ کی حدود سے بچا جا سکے۔
    """
    def __init__(self):
        self.all_keys: List[str] = []
        self.key_pool: List[str] = []
        self.pair_to_key_map: Dict[str, str] = {}
        self._initialize_keys()

    def _initialize_keys(self):
        """
        کنفیگریشن سے کیز لوڈ کرتا ہے اور انہیں جوڑوں کو تفویض کرتا ہے۔
        """
        self.all_keys = sorted(list(set(api_settings.twelve_data_keys_list)))
        
        if not self.all_keys:
            logger.critical("کوئی بھی Twelve Data API کلید فراہم نہیں کی گئی۔ سسٹم کام نہیں کر سکتا۔")
            return

        # تمام ممکنہ جوڑوں کی ایک منفرد اور ترتیب شدہ فہرست بنائیں
        all_pairs = sorted(list(set(
            trading_settings.WEEKDAY_PRIMARY +
            trading_settings.WEEKDAY_BACKUP +
            trading_settings.WEEKEND_PRIMARY +
            trading_settings.WEEKEND_BACKUP
        )))

        logger.info(f"Key Manager شروع کیا جا رہا ہے: کل {len(self.all_keys)} کیز اور {len(all_pairs)} جوڑے۔")

        if len(self.all_keys) < len(all_pairs):
            logger.warning(
                f"API کیز کی تعداد ({len(self.all_keys)}) جوڑوں کی تعداد ({len(all_pairs)}) سے کم ہے۔ "
                "کچھ جوڑے ایک ہی کلید استعمال کریں گے۔"
            )

        # ہر جوڑے کو ایک کلید تفویض کریں
        keys_to_assign = self.all_keys.copy()
        for pair in all_pairs:
            if not keys_to_assign:
                # اگر کیز ختم ہو جائیں تو شروع سے دوبارہ تفویض کریں (چکر)
                keys_to_assign = self.all_keys.copy()
            
            key = keys_to_assign.pop(0)
            self.pair_to_key_map[pair] = key
            logger.info(f"جوڑا '{pair}' کو کلید '...{key[-8:]}' تفویض کی گئی۔")

        # باقی بچ جانے والی کیز کو بیک اپ پول میں ڈالیں
        self.key_pool = keys_to_assign
        if self.key_pool:
            logger.info(f"{len(self.key_pool)} اضافی کیز بیک اپ پول میں دستیاب ہیں۔")

    def get_key_for_pair(self, symbol: str) -> Optional[str]:
        """کسی مخصوص جوڑے کے لیے تفویض کردہ کلید واپس کرتا ہے۔"""
        key = self.pair_to_key_map.get(symbol)
        if not key:
            logger.warning(f"جوڑے '{symbol}' کے لیے کوئی مخصوص کلید نہیں ملی۔ بیک اپ کلید استعمال کی جا رہی ہے۔")
            return self.get_backup_key()
        return key

    def get_backup_key(self) -> Optional[str]:
        """بیک اپ پول سے ایک کلید واپس کرتا ہے یا پہلی کلید اگر پول خالی ہو۔"""
        if self.key_pool:
            # راؤنڈ روبن طریقے سے ایک بیک اپ کلید منتخب کریں
            key = self.key_pool.pop(0)
            self.key_pool.append(key)
            return key
        
        if self.all_keys:
            # اگر کوئی بیک اپ کلید نہیں ہے، تو پہلی کلید واپس کریں
            logger.warning("بیک اپ پول خالی ہے۔ پہلی دستیاب کلید استعمال کی جا رہی ہے۔")
            return self.all_keys[0]
            
        return None

# سنگلٹن مثال تاکہ پوری ایپلیکیشن میں ایک ہی مینیجر استعمال ہو
key_manager = KeyManager()
            
