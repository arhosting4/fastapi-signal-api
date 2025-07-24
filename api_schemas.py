from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

# ===================================================================
# FINAL CORRECTED VERSION WITH Pydantic V2 COMPATIBILITY
# ===================================================================

class Signal(BaseModel):
    signal_id: str
    symbol: str
    timeframe: str
    signal_type: str
    entry_price: float
    tp_price: float
    sl_price: float
    confidence: float
    reason: str
    created_at: datetime

    # Pydantic V2 کے لیے درست کنفیگریشن
    model_config = ConfigDict(from_attributes=True)

class Trade(BaseModel):
    symbol: str
    entry_price: float
    outcome: str
    closed_at: datetime

    # Pydantic V2 کے لیے درست کنفیگریشن
    model_config = ConfigDict(from_attributes=True)

class Summary(BaseModel):
    win_rate: float
    pnl: float

class NewsArticle(BaseModel):
    title: str
    url: str
    source: str
    snippet: str

class NewsResponse(BaseModel):
    message: str
    data: List[NewsArticle]
