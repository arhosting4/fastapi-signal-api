# filename: key_manager.py

import os
import time
import logging
from typing import List, Dict, Optional
from collections import deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ==================================================================
# 🔑 KeyManager: API keys ko manage karne ka smart system
# Guardian aur Hunter keys alag pool mein distribute ki jati hain
# ==================================================================

class KeyManager:
    def __init__(self):
        """
        KeyManager ka initializer.
        Ye system .env se keys load karta hai aur unhe guardian/hunter pools mein distribute karta hai.
        """
        self.guardian_keys: deque[str] = deque()
        self.hunter_keys: deque[str] = deque()
        self.limited_keys: Dict[str, float] = {}  # ⏱️ Limited keys with expiry timestamps
        self.load_and_distribute_keys()

    def load_and_distribute_keys(self):
        """
        🌐 Environment se API keys load karo aur unhe do pools mein split karo.
        Supports:
          - TWELVE_DATA_API_KEYS (comma-separated)
          - TWELVE_DATA_API_KEY_1, _2, ...
        """
        all_keys = []

        # 1️⃣ Comma-separated key string
        keys_str = os.getenv("TWELVE_DATA_API_KEYS", "")
        if keys_str:
            all_keys.extend(key.strip() for key in keys_str.split(',') if key.strip())

        # 2️⃣ Numbered keys (TWELVE_DATA_API_KEY_1, 2, ...)
        i = 1
        while True:
            key = os.getenv(f"TWELVE_DATA_API_KEY_{i}")
            if not key:
                break
            all_keys.append(key.strip())
            i += 1

        # 🔀 Alternate assignment: Even-index → guardian, Odd-index → hunter
        for idx, key in enumerate(all_keys):
            if idx % 2 == 0:
                self.guardian_keys.append(key)
            else:
                self.hunter_keys.append(key)

        logger.info(f"{len(self.guardian_keys)} guardian keys | {len(self.hunter_keys)} hunter keys loaded.")

    def get_next_key(self, bot_type: str) -> Optional[str]:
        """
        🔁 Returns a non-limited API key for given bot_type: "guardian" or "hunter".
        Automatically skips expired keys.
        """
        pool = self.guardian_keys if bot_type == "guardian" else self.hunter_keys

        for _ in range(len(pool)):
            key = pool.popleft()
            expiry = self.limited_keys.get(key)

            # Agar key expired hai, skip karo
            if not expiry or time.time() > expiry:
                self.limited_keys.pop(key, None)
                pool.append(key)  # Queue ke end mein daal do
                return key
            else:
                # Waqti disable hai, end mein daal ke agli check karo
                pool.append(key)

        logger.warning(f"No available keys for bot: {bot_type}")
        return None

    def limit_key(self, key: str, minutes: int = 1):
        """
        ⏳ Kisi key ko temporarily disable karo for `minutes` time.
        """
        self.limited_keys[key] = time.time() + minutes * 60
        logger.info(f"Key temporarily disabled: {key} for {minutes} minutes")
