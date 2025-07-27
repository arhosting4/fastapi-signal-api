# filename: database_crud.py

from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from models import CompletedTrade, FeedbackEntry, CachedNews, ActiveSignal

logger = logging.getLogger(__name__)

# ==============================================================================
# فعال سگنلز کے لیے فنکشنز
# ==============================================================================

def get_active_signal_by_symbol(db: Session, symbol: str) -> Optional[ActiveSignal]:
    """کسی علامت کے لیے فعال سگنل واپس کرتا ہے۔"""
    return db.query(ActiveSignal).filter(ActiveSignal.symbol == symbol).first()

def get_all_active_signals_from_db(db: Session) -> List[ActiveSignal]:
    """ڈیٹا بیس سے تمام فعال سگنلز کی فہرست واپس کرتا ہے۔"""
    return db.query(ActiveSignal).order_by(desc(ActiveSignal.created_at)).all()

# ★★★ نیا فنکشن جو غائب تھا ★★★
def get_active_signals_count(db: Session) -> int:
    """ڈیٹا بیس میں موجود فعال سگنلز کی کل تعداد واپس کرتا ہے۔"""
    return db.query(func.count(ActiveSignal.id)).scalar() or 0

def add_or_update_active_signal(db: Session, signal_data: Dict[str, Any]) -> ActiveSignal:
    """ایک نیا فعال سگنل شامل کرتا ہے یا اگر اسی علامت کے لیے پہلے سے موجود ہو تو اسے اپ ڈیٹ کرتا ہے۔"""
    existing_signal = get_active_signal_by_symbol(db, signal_data['symbol'])
    
    if existing_signal:
        existing_signal.entry_price = signal_data['price']
        existing_signal.tp_price = signal_data['tp']
        existing_signal.sl_price = signal_data['sl']
        existing_signal.confidence = signal_data['confidence']
        existing_signal.reason = signal_data['reason']
        existing_signal.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_signal)
        return existing_signal
    else:
        new_signal = ActiveSignal(
            signal_id=f"{signal_data['symbol']}_{signal_data['timeframe']}_{datetime.utcnow().timestamp()}",
            symbol=signal_data['symbol'],
            timeframe=signal_data['timeframe'],
            signal_type=signal_data['signal'],
            entry_price=signal_data['price'],
            tp_price=signal_data['tp'],
            sl_price=signal_data['sl'],
            confidence=signal_data['confidence'],
            reason=signal_data['reason'],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(new_signal)
        db.commit()
        db.refresh(new_signal)
        return new_signal

# ... (باقی تمام فنکشنز ویسے ہی رہیں گے) ...
