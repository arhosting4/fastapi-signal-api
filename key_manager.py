import logging
import itertools
from typing import Dict, Optional, List

from config import api_settings
from roster_manager import get_active_trading_pairs # <--- یہ اب کام کرے گا

logger = logging.getLogger(__name__)

class KeyManager:
    def __init__(self):
        self.keys: List[str] = api_settings.twelve_data_keys_list
        self.pair_to_key_map: Dict[str, str] = {}
        self.backup_key_cycler = itertools.cycle(self.keys)
        self._assign_keys_to_pairs()

    def _assign_keys_to_pairs(self):
        """جوڑوں کو API کیز تفویض کرتا ہے۔"""
        trading_pairs = get_active_trading_pairs()
        
        if not self.keys:
            logger.critical("کوئی Twelve Data API کلید فراہم نہیں کی گئی۔")
            return

        for i, pair in enumerate(trading_pairs):
            # ہر جوڑے کو ایک کلید تفویض کریں، اگر کیز ختم ہو جائیں تو دوبارہ شروع کریں
            self.pair_to_key_map[pair] = self.keys[i % len(self.keys)]
        
        logger.info(f"{len(self.pair_to_key_map)} جوڑوں کو API کیز کامیابی سے تفویض کی گئیں۔")

    def get_key(self, symbol: str) -> Optional[str]:
        """کسی مخصوص جوڑے کے لیے تفویض کردہ کلید فراہم کرتا ہے یا بیک اپ کلید دیتا ہے۔"""
        if not self.keys:
            return None
            
        key = self.pair_to_key_map.get(symbol)
        if key:
            return key
        
        # اگر کسی وجہ سے مخصوص کلید نہ ملے (مثلاً کرپٹو کے لیے)
        logger.warning(f"جوڑے '{symbol}' کے لیے کوئی مخصوص کلید نہیں ملی۔ بیک اپ کلید استعمال کی جا رہی ہے۔")
        return next(self.backup_key_cycler)

    def get_key_status(self) -> Dict[str, int]:
        """موجودہ کلیدوں کی حالت واپس کرتا ہے۔"""
        return {
            "total_keys": len(self.keys),
            "assigned_pairs": len(self.pair_to_key_map)
        }

key_manager = KeyManager()
