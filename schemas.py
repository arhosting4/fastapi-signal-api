# filename: schemas.py
"""
Pydantic اسکیمیں ڈیٹا کی توثیق کے لیے
"""
from pydantic import BaseModel, Field
from typing import List, Optional

class Candle(BaseModel):
    """OHLC کینڈل ڈیٹا کی توثیق کرتا ہے"""
    datetime: str
    open: str  # API سے سٹرنگ کے طور پر آتا ہے، بعد میں تبدیل کریں گے
    high: str
    low: str
    close: str
    volume: Optional[str] = None
    # ★★★ نیا اختیاری وصف ★★★
    # یہ وصف utils.py میں ڈیٹا حاصل کرنے کے بعد شامل کیا جائے گا
    symbol: Optional[str] = None

class TwelveDataTimeSeries(BaseModel):
    """Twelve Data API سے آنے والے ٹائم سیریز کے جواب کی توثیق کرتا ہے"""
    meta: Dict[str, Any] # میٹا ڈیٹا کو بھی شامل کر لیں تاکہ علامت کا نام مل سکے
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
    
