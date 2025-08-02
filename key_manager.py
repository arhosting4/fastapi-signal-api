# filename: key_manager.py

import os
import threading
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class APIKey:
    def __init__(self, key: str):
        self.key = key
        self.credits_today = 0
        self.credits_minute = 0
        self.last_minute = None
        self.exhausted = False
        self.cooldown_until = None

class KeyManager:
    """
    TwelveData API key pool manager.
    Handles quota rotation, per-minute/day limit, thread safety, auto-failover/reset.
    Only public access via get_hunter_key()/get_guardian_key().
    """
    def __init__(self, keys, reset_hour_utc=0):
        self.keys = [APIKey(k.strip()) for k in keys if k.strip()]
        self.lock = threading.Lock()
        self.reset_hour_utc = reset_hour_utc
        self._last_daily_reset = None
    
    def _reset_daily(self):
        now = datetime.utcnow()
        if self._last_daily_reset != now.date() and now.hour == self.reset_hour_utc:
            for k in self.keys:
                k.credits_today = 0
                k.exhausted = False
                k.cooldown_until = None
            self._last_daily_reset = now.date()
            logger.info("API keys daily quota counters have been reset.")
    
    def _reset_minute(self):
        now = datetime.utcnow().replace(second=0, microsecond=0)
        for k in self.keys:
            if k.last_minute != now:
                k.credits_minute = 0
                k.last_minute = now

    def get_hunter_key(self):
        """For OHLC/candles data fetches."""
        self._reset_daily()
        self._reset_minute()
        with self.lock:
            for k in self.keys:
                if k.exhausted:
                    continue
                if k.cooldown_until and datetime.utcnow() < k.cooldown_until:
                    continue
                if k.credits_today >= 800:
                    k.exhausted = True
                    continue
                if k.credits_minute >= 8:
                    k.cooldown_until = datetime.utcnow() + timedelta(minutes=1)
                    continue
                k.credits_today += 1
                k.credits_minute += 1
                logger.debug(f"Hunter key selected: {k.key} (today={k.credits_today}, min={k.credits_minute})")
                return k.key
        logger.warning("All Hunter keys are currently unavailable (exhausted/cooldown).")
        return None

    def get_guardian_key(self):
        """For quotes/monitor requests. Separated for future logic expansion."""
        return self.get_hunter_key()

    def report_key_issue(self, key, is_daily_limit=False):
        """Handles 429s: marks key as exhausted/cooldown as needed."""
        with self.lock:
            for k in self.keys:
                if k.key == key:
                    if is_daily_limit:
                        k.exhausted = True
                        logger.info(f"Key {key} marked exhausted (day quota).")
                    else:
                        k.cooldown_until = datetime.utcnow() + timedelta(minutes=1)
                        logger.info(f"Key {key} cooldown for 1 minute (minute quota breach).")
                    return

def load_keys_from_env():
    keys = os.getenv("TWELVEDATA_API_KEYS", "")
    return keys.split(',') if keys else []

key_manager = KeyManager(load_keys_from_env())
                
