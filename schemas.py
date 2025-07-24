# filename: schemas.py
"""
Pydantic اسکیمیں ڈیٹا کی توثیق کے لیے
"""
from pydantic import BaseModel, Field
from typing import List, Optional

class Candle(BaseModel):
    """OHLC کینڈل ڈیٹا کی توثیق کرتا ہے"""
    datetime: str
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None

class TwelveDataTimeSeries(BaseModel):
    """Twelve Data API سے آنے والے ٹائم سیریز کے جواب کی توثیق کرتا ہے"""
    values: List[Candle]
    status: str

class SignalData(BaseModel):
    """سگنل ڈیٹا کی ساخت کی توثیق کرتا ہے"""
    signal_id: str
    symbol: str
    timeframe: str
    signal: str = Field(alias="signal_type")
    price: float = Field(alias="entry_price")
    tp: float = Field(alias="tp_price")
    sl: float = Field(alias="sl_price")
    confidence: float
    reason: str
    timestamp: str
    
