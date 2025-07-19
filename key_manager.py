import os
import time
from typing import List, Optional

class TwelveDataKeyManager:
    def __init__(self):
        self.api_keys = self._load_api_keys()
        self.current_key_index = 0
        self.failed_keys = set()
        self.last_request_time = {}
        self.min_request_interval = 1  # Minimum seconds between requests per key
    
    def _load_api_keys(self) -> List[str]:
        """Load API keys from environment variables"""
        keys = []
        
        # Try to load multiple keys
        for i in range(1, 6):  # Support up to 5 keys
            key_name = f"TWELVE_DATA_API_KEY_{i}" if i > 1 else "TWELVE_DATA_API_KEY"
            key = os.getenv(key_name)
            if key:
                keys.append(key)
        
        if not keys:
            print("WARNING: No Twelve Data API keys found in environment variables")
        else:
            print(f"Loaded {len(keys)} Twelve Data API keys")
        
        return keys
    
    def get_next_key(self) -> Optional[str]:
        """Get the next available API key"""
        if not self.api_keys:
            return None
        
        # Try to find a working key
        attempts = 0
        while attempts < len(self.api_keys):
            key = self.api_keys[self.current_key_index]
            
            # Skip failed keys
            if key not in self.failed_keys:
                # Check rate limiting
                current_time = time.time()
                last_used = self.last_request_time.get(key, 0)
                
                if current_time - last_used >= self.min_request_interval:
                    self.last_request_time[key] = current_time
                    return key
            
            # Move to next key
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            attempts += 1
        
        # If all keys are failed or rate limited, wait and try again
        time.sleep(2)
        return self.api_keys[self.current_key_index] if self.api_keys else None
    
    def mark_key_failed(self, api_key: str):
        """Mark an API key as failed"""
        self.failed_keys.add(api_key)
        print(f"Marked API key as failed: {api_key[:10]}...")
        
        # If all keys are failed, reset the failed set after some time
        if len(self.failed_keys) >= len(self.api_keys):
            print("All API keys failed, resetting after 60 seconds...")
            time.sleep(60)
            self.failed_keys.clear()
    
    def reset_failed_keys(self):
        """Reset all failed keys (useful for periodic cleanup)"""
        self.failed_keys.clear()
        print("Reset all failed API keys")
    
    def get_key_status(self) -> dict:
        """Get status of all API keys"""
        return {
            "total_keys": len(self.api_keys),
            "failed_keys": len(self.failed_keys),
            "working_keys": len(self.api_keys) - len(self.failed_keys),
            "current_key_index": self.current_key_index
        }

# Global instance
key_manager = TwelveDataKeyManager()
