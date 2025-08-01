# filename: key_manager.py

import os
import time
import logging
from typing import List, Dict, Optional
from collections import deque
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

class KeyManager:
    def __init__(self):
        self.guardian_keys: deque[str] = deque()
        self.hunter_keys: deque[str] = deque()
        self.limited_keys: Dict[str, float] = {}
        self.load_and_distribute_keys()

    def load_and_distribute_keys(self):
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
            logger.error(f"At least 9 unique API keys are required. Found: {len(unique_keys)}")
            guardian_pool_size = min(5, len(unique_keys) - 4) if len(unique_keys) > 4 else len(unique_keys)
        else:
            guardian_pool_size = 5

        self.guardian_keys = deque(unique_keys[:guardian_pool_size])
        self.hunter_keys = deque(unique_keys[guardian_pool_size:])

        logger.info(f"KeyManager started with {len(unique_keys)} unique keys.")
        logger.info(f"Guardian Pool: {len(self.guardian_keys)} keys")
        logger.info(f"Hunter Pool: {len(self.hunter_keys)} keys")

    def _get_key_from_pool(self, pool: deque[str]) -> Optional[str]:
        if not pool:
            return None
        for _ in range(len(pool)):
            key = pool[0]
            pool.rotate(-1)
            if key in self.limited_keys:
                if time.time() > self.limited_keys[key]:
                    del self.limited_keys[key]
                    return key
                else:
                    continue
            else:
                return key
        return None

    def get_guardian_key(self) -> Optional[str]:
        return self._get_key_from_pool(self.guardian_keys)

    def get_hunter_key(self) -> Optional[str]:
        return self._get_key_from_pool(self.hunter_keys)

    def get_main_key(self) -> Optional[str]:
        return self.guardian_keys[0] if self.guardian_keys else None

    def report_key_issue(self, key: str, is_daily_limit: bool):
        if key in self.limited_keys:
            return
        if is_daily_limit:
            now_utc = datetime.now(timezone.utc)
            tomorrow_utc = now_utc + timedelta(days=1)
            midnight_utc = tomorrow_utc.replace(hour=0, minute=0, second=1, microsecond=0)
            expiry_timestamp = midnight_utc.timestamp()
        else:
            expiry_timestamp = time.time() + 65
        self.limited_keys[key] = expiry_timestamp

key_manager = KeyManager()
