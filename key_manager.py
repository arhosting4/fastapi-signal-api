import os
import json
from typing import List, Optional

# یہ فائل ٹریک کرے گی کہ کون سی کلید اس وقت فعال ہے
STATE_FILE = "data/key_manager_state.json"

class KeyManager:
    def __init__(self):
        self.keys: List[str] = self._load_keys_from_env()
        self.current_key_index: int = self._load_state()
        if not self.keys:
            raise ValueError("No Twelve Data API keys found in environment variables (e.g., TWELVE_DATA_API_KEY_1).")

    def _load_keys_from_env(self) -> List[str]:
        """ماحول سے تمام API کلیدوں کو لوڈ کرتا ہے۔"""
        loaded_keys = []
        i = 1
        while True:
            key = os.getenv(f"TWELVE_DATA_API_KEY_{i}")
            if key:
                loaded_keys.append(key)
                i += 1
            else:
                break
        print(f"KeyManager: Found {len(loaded_keys)} API keys.")
        return loaded_keys

    def _load_state(self) -> int:
        """محفوظ کردہ حالت سے موجودہ کلید کا انڈیکس لوڈ کرتا ہے۔"""
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
                return state.get("current_key_index", 0)
        except (FileNotFoundError, json.JSONDecodeError):
            return 0

    def _save_state(self):
        """موجودہ کلید کے انڈیکس کو فائل میں محفوظ کرتا ہے۔"""
        state = {"current_key_index": self.current_key_index}
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)

    def get_current_key(self) -> str:
        """موجودہ فعال API کلید واپس کرتا ہے۔"""
        return self.keys[self.current_key_index]

    def rotate_to_next_key(self) -> Optional[str]:
        """
        اگلی API کلید پر منتقل ہوتا ہے۔ اگر تمام کلیدیں استعمال ہو چکی ہوں تو None واپس کرتا ہے۔
        """
        print(f"KeyManager: Rotating from key index {self.current_key_index}.")
        self.current_key_index += 1
        if self.current_key_index >= len(self.keys):
            print("KeyManager: All API keys have been exhausted for the day.")
            # اگر تمام کلیدیں ختم ہو جائیں تو واپس شروع میں چلے جائیں (اگلے دن کے لیے)
            self.current_key_index = 0 
            self._save_state()
            return None # آج کے لیے کوئی مزید کلید نہیں
        
        self._save_state()
        new_key = self.get_current_key()
        print(f"KeyManager: Rotated to new key index {self.current_key_index}.")
        return new_key

# ایک عالمی مینیجر بنائیں تاکہ پوری ایپ اسے استعمال کر سکے
key_manager = KeyManager()
