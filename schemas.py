# filename: schemas.py

"""
Pydantic اسکیمیں API کی درخواستوں، جوابات، اور اندرونی ڈیٹا کی ساختوں کی توثیق کے لیے۔
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- بنیادی ڈیٹا کی ساختیں ---

class Candle(BaseModel):
    """
    OHLCV کینڈل ڈیٹا کی نمائندگی کرتا ہے۔
    یہ Twelve Data API سے آنے والے ڈیٹا کی توثیق کرتا ہے۔
    """
    datetime: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    symbol: Optional[str] = None

    # اصلاح: یہ ویلیڈیٹر یقینی بنائے گا کہ API سے آنے والی سٹرنگ ویلیوز فلوٹ میں تبدیل ہو جائیں
    @field_validator('open', 'high', 'low', 'close', 'volume', mode='before')
    @classmethod
    def clean_float(cls, v: Any) -> Optional[float]:
        if v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            # اگر قیمت کو فلوٹ میں تبدیل نہیں کیا جا سکتا تو اسے نظر انداز کریں
            return None

class TwelveDataTimeSeries(BaseModel):
    """
    Twelve Data API سے آنے والے ٹائم سیریز کے جواب کی مکمل ساخت کی توثیق کرتا ہے۔
    """
    meta: Dict[str, Any]
    values: List[Candle]
    status: str

# --- API رسپانس ماڈلز ---

class ActiveSignalResponse(BaseModel):
    """/api/active-signals اینڈ پوائنٹ کے لیے رسپانس ماڈل۔"""
    id: int
    signal_id: str
    symbol: str
    timeframe: str
    signal_type: str
    entry_price: float
    tp_price: float
    sl_price: float
    confidence: float
    reason: str
    component_scores: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    is_new: bool

class DailyStatsResponse(BaseModel):
    """/api/daily-stats اینڈ پوائنٹ کے لیے رسپانس ماڈل۔"""
    tp_hits_today: int
    sl_hits_today: int
    live_signals: int
    win_rate_today: float

class HistoryResponse(BaseModel):
    """/api/history اینڈ پوائنٹ کے لیے رسپانس ماڈل۔"""
    id: int
    signal_id: str
    symbol: str
    timeframe: str
    signal_type: str
    entry_price: float
    tp_price: float
    sl_price: float
    close_price: Optional[float] = None
    reason_for_closure: Optional[str] = None
    outcome: str
    confidence: float
    reason: str
    closed_at: datetime

class NewsArticle(BaseModel):
    """ایک انفرادی خبر کے مضمون کی ساخت۔"""
    title: str
    url: str
    source: str
    snippet: str
    published_at: str
    impact: str
    entities: List[str]

class NewsResponse(BaseModel):
    """/api/news اینڈ پوائنٹ کے لیے رسپانس ماڈل۔"""
    articles_by_symbol: Dict[str, List[NewsArticle]]

class KeyStatusResponse(BaseModel):
    """API کیز کی حالت کی تفصیلات۔"""
    total_keys: int
    available_keys: int
    limited_keys_now: int

class SystemStatusResponse(BaseModel):
    """/api/system-status اینڈ پوائنٹ کے لیے رسپانس ماڈل۔"""
    server_status: str
    timestamp_utc: datetime
    scheduler_status: str
    database_status: str
    key_status: KeyStatusResponse
    
