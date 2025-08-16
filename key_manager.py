import logging
import itertools
from typing import Dict, Optional, List

from config import api_settings
from roster_manager import get_active_trading_pairs

logger = logging.getLogger(__name__)

class KeyManager:
    def __init__(self):
        self.keys: List[str] = api_settings.twelve_data_keys_list
        self.pair_to_key_map: Dict[str, str] = {}
        # ★★★ اہم تبدیلی: بیک اپ کیز کو ایک الگ فہرست میں رکھیں ★★★
        self.backup_keys = self.keys[7:]  # آخری 2 کیز بیک اپ کے لیے
        self.backup_key_cycler = itertools.cycle(self.backup_keys) if self.backup_keys else itertools.cycle(self.keys)
        self._assign_keys_to_pairs()

    def _assign_keys_to_pairs(self):
        """جوڑوں کو API کیز تفویض کرتا ہے۔"""
        # صرف فاریکس جوڑوں کو مخصوص کیز تفویض کریں
        trading_pairs = get_active_trading_pairs()
        
        # صرف پہلی 7 کیز استعمال کریں
        dedicated_keys = self.keys[:7]

        if not dedicated_keys:
            logger.critical("کوئی مخصوص Twelve Data API کلید فراہم نہیں کی گئی۔")
            return

        for i, pair in enumerate(trading_pairs):
            if i < len(dedicated_keys):
                self.pair_to_key_map[pair] = dedicated_keys[i]
        
        logger.info(f"{len(self.pair_to_key_map)} جوڑوں کو API کیز کامیابی سے تفویض کی گئیں۔")

    # ★★★ یہ ہے وہ فنکشن جس کا نام غلط تھا ★★★
    def get_key_for_pair(self, symbol: str) -> Optional[str]:
        """کسی مخصوص جوڑے کے لیے تفویض کردہ کلید فراہم کرتا ہے یا بیک اپ کلید دیتا ہے۔"""
        if not self.keys:
            return None
            
        key = self.pair_to_key_map.get(symbol)
        if key:
            return key
        
        logger.warning(f"جوڑے '{symbol}' کے لیے کوئی مخصوص کلید نہیں ملی۔ بیک اپ کلید استعمال کی جا رہی ہے۔")
        return next(self.backup_key_cycler)

    def get_key_status(self) -> Dict[str, any]:
        """موجودہ کلیدوں کی حالت واپس کرتا ہے۔"""
        return {
            "total_keys": len(self.keys),
            "dedicated_keys": len(self.keys[:7]),
            "backup_keys": len(self.backup_keys),
            "assigned_pairs": len(self.pair_to_key_map)
        }

key_manager = KeyManager()
                
