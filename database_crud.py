# database_crud.py

from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.database.models import CompletedTrade, FeedbackEntry, CachedNews

def add_completed_trade(db: Session, signal_data: Dict[str, Any], outcome: str):
    required_keys = ['signal_id', 'symbol', 'timeframe', 'signal', 'price', 'tp', 'sl']
    if not all(key in signal_data for key in required_keys):
        return None
    db_trade = CompletedTrade(
        signal_id=signal_data['signal_id'], symbol=signal_data['symbol'],
        timeframe=signal_data['timeframe'], signal_type=signal_data['signal'],
        entry_price=signal_data['price'], tp_price=signal_data['tp'],
        sl_price=signal_data['sl'], outcome=outcome, closed_at=datetime.utcnow()
    )
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade

def add_feedback_entry(db: Session, symbol: str, timeframe: str, feedback: str):
    db_feedback = FeedbackEntry(
        symbol=symbol, timeframe=timeframe, feedback=feedback
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

def get_completed_trades(db: Session, limit: int = 100) -> List[CompletedTrade]:
    return db.query(CompletedTrade).order_by(desc(CompletedTrade.closed_at)).limit(limit).all()

def update_news_cache(db: Session, news_data: Dict[str, Any]):
    db.query(CachedNews).delete()
    db_news = CachedNews(content=news_data, updated_at=datetime.utcnow())
    db.add(db_news)
    db.commit()
    return db_news

def get_cached_news(db: Session) -> Optional[Dict[str, Any]]:
    news_item = db.query(CachedNews).order_by(desc(CachedNews.updated_at)).first()
    return news_item.content if news_item else None```

**تیسری گمشدہ فائل: `key_manager.py`**

یہ فائل API کلیدوں کو منظم کرنے کے لیے ہے۔

1.  اپنے پروجیکٹ کے **مرکزی (root)** فولڈر میں، `key_manager.py` نامی ایک **نئی فائل** بنائیں۔
2.  اس نئی فائل میں درج ذیل کوڈ کو کاپی اور پیسٹ کریں۔

```python
# key_manager.py

import os
import time
from typing import List, Optional

class KeyManager:
    def __init__(self):
        self.keys: List[str] = []
        self.limited_keys: Dict[str, float] = {}
        self.load_keys()

    def load_keys(self):
        api_keys_str = os.getenv("TWELVE_DATA_API_KEYS", "")
        self.keys = [key.strip() for key in api_keys_str.split(',') if key.strip()]
        print(f"KeyManager: Found {len(self.keys)} API keys.")

    def get_api_key(self) -> Optional[str]:
        current_time = time.time()
        for key in self.keys:
            if key not in self.limited_keys or current_time - self.limited_keys[key] > 60:
                if key in self.limited_keys:
                    del self.limited_keys[key]
                return key
        
        print("KeyManager: All keys are currently rate-limited.")
        return None

    def mark_key_as_limited(self, key: str):
        print(f"KeyManager: API key limit reached for key ending in ...{key[-4:]}. Rotating.")
        self.limited_keys[key] = time.time()

key_manager = KeyManager()
