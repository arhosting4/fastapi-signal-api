# filename: schemas.py

"""
Pydantic اسکیمیں ڈیٹا کی توثیق کے لیے (OHLC، Time Series، Signals وغیرہ)
پورے پروجیکٹ میں centralized, no conflict, audit/upgrade-ready structure!
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any

class Candle(BaseModel):
    """OHLC کینڈل ڈیٹا کی توثیق (API, DB, ہر analysis module کے لیے)"""
    datetime: str
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    symbol: Optional[str] = None

    @validator('open', 'high', 'low', 'close', 'volume', pre=True)
    def clean_float(cls, v):
        """
        یقینی بناتا ہے کہ فلوٹ ہی استعمال ہو — اگر اسٹارنگ/None آئے تو gracefully ignore کرے۔
        """
        if v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

class TwelveDataTimeSeries(BaseModel):
    """Twelve Data API سے آنے والے ٹائم سیریز کے جواب کی توثیق کرتا ہے"""
    meta: Dict[str, Any]
    values: List[Candle]
    status: str

class SignalData(BaseModel):
    """سگنل ڈیٹا کی ساخت کی توثیق (DB/API/ws بندرگاہ)"""
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

# اگر future میں bulk ingest یا output needed:
class BulkSignalRequest(BaseModel):
    """متعدد سگنلز کی ایک ساتھ API ingestion/backup کے لیے support"""
    signals: List[SignalData]
    
