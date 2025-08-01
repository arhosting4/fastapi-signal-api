# filename: schemas.py
"""
Pydantic اسکیمیں ڈیٹا کی توثیق کے لیے
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any

class Candle(BaseModel):
    """OHLC کینڈل ڈیٹا کی توثیق کرتا ہے"""
    datetime: str
    # ★★★ قسم کو واپس float میں تبدیل کر دیا گیا ہے ★★★
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    symbol: Optional[str] = None

    # یہ ایک ویلیڈیٹر ہے جو یقینی بنائے گا کہ API سے آنے والی سٹرنگ ویلیوز فلوٹ میں تبدیل ہو جائیں
    @validator('open', 'high', 'low', 'close', 'volume', pre=True)
    def clean_float(cls, v):
        if v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            # اگر قیمت کو فلوٹ میں تبدیل نہیں کیا جا سکتا تو ڈیفالٹ ویلیو دیں یا خرابی پیدا کریں
            # یہاں ہم اسے None کر رہے ہیں تاکہ بعد میں اسے نظر انداز کیا جا سکے
            return None

class TwelveDataTimeSeries(BaseModel):
    """Twelve Data API سے آنے والے ٹائم سیریز کے جواب کی توثیق کرتا ہے"""
    meta: Dict[str, Any]
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
    timestamp: str
    
