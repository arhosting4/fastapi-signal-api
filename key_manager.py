# filename: key_manager.py

import logging
from typing import Dict, Optional, List

from config import api_settings
# roster_manager سے get_active_trading_pairs کو امپورٹ کریں
from roster_manager import get_active_trading_pairs

logger = logging.getLogger(__name__)

class KeyManager:
    def __init__(self):
        self.all_keys: List[str] = []
        self.key_pool: List[str] = []
        self.pair_to_key_map: Dict[str, str] = {}
        self._initialize_keys()

    def _initialize_keys(self):
        self.all_keys = sorted(list(set(api_settings.twelve_data_keys_list)))
        if not self.all_keys:
            logger.critical("کوئی بھی Twelve Data API کلید فراہم نہیں کی گئی۔")
            return

        # صرف آج کے فعال جوڑوں کی فہرست حاصل کریں
        active_pairs = get_active_trading_pairs()
        logger.info(f"Key Manager شروع کیا جا رہا ہے: {len(self.all_keys)} کیز اور {len(active_pairs)} فعال جوڑے۔")

        # ہر فعال جوڑے کو ایک کلید تفویض کریں
        keys_to_assign = self.all_keys.copy()
        for pair in active_pairs:
            if not keys_to_assign:
                keys_to_assign = self.all_keys.copy()
            
            key = keys_to_assign.pop(0)
            self.pair_to_key_map[pair] = key
            logger.info(f"فعال جوڑا '{pair}' کو کلید '...{key[-8:]}' تفویض کی گئی۔")

        self.key_pool = keys_to_assign
        if self.key_pool:
            logger.info(f"{len(self.key_pool)} اضافی کیز بیک اپ پول میں دستیاب ہیں۔")

    def get_key_for_pair(self, symbol: str) -> Optional[str]:
        key = self.pair_to_key_map.get(symbol)
        if not key:
            logger.warning(f"جوڑے '{symbol}' کے لیے کوئی مخصوص کلید نہیں ملی۔ بیک اپ کلید استعمال کی جا رہی ہے۔")
            return self.get_backup_key()
        return key

    def get_backup_key(self) -> Optional[str]:
        if self.key_pool:
            key = self.key_pool[0]
            self.key_pool.append(self.key_pool.pop(0))
            return key
        if self.all_keys:
            return self.all_keys[0]
        return None

key_manager = KeyManager()
