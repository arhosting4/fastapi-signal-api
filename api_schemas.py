from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

# --- Base Models for consistent typing ---
class SignalBase(BaseModel):
    symbol: str
    timeframe: str
    signal_type: str
    entry_price: float
    tp_price: float
    sl_price: float

# --- Response Models for API Endpoints ---

class ActiveSignal(SignalBase):
    id: int
    signal_id: str
    confidence: float
    reason: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True

class TradeHistory(SignalBase):
    id: int
    signal_id: str
    outcome: str
    created_at: datetime
    closed_at: datetime

    class Config:
        orm_mode = True

class NewsItem(BaseModel):
    title: str
    url: str
    source: str
    image_url: str
    snippet: str

class News(BaseModel):
    message: Optional[str] = None
    data: Optional[List[NewsItem]] = None

class Summary(BaseModel):
    win_rate_24h: float
    today_pl: float
  
