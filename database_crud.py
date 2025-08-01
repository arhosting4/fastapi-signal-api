# filename: database_crud.py

from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, NamedTuple
import logging

# 📦 ماڈلز امپورٹ کریں
from models import ActiveSignal, CompletedTrade, FeedbackEntry, CachedNews

logger = logging.getLogger(__name__)

# ==============================================================================
# 🧾 سگنل اپڈیٹ کا نتیجہ (نیا ہے یا پرانا)
# ==============================================================================
class SignalUpdateResult(NamedTuple):
    signal: ActiveSignal
    is_new: bool

# ==============================================================================
# 📊 فعال سگنلز گنیں
# ==============================================================================
def get_active_signals_count_from_db(db: Session) -> int:
    return db.query(func.count(ActiveSignal.id)).scalar() or 0

# ==============================================================================
# 📋 تمام فعال سگنلز حاصل کریں
# ==============================================================================
def get_all_active_signals_from_db(db: Session) -> List[ActiveSignal]:
    return db.query(ActiveSignal).all()

# ==============================================================================
# 🔍 کسی symbol کا فعال سگنل حاصل کریں
# ==============================================================================
def get_active_signal_by_symbol(db: Session, symbol: str) -> Optional[ActiveSignal]:
    return db.query(ActiveSignal).filter(ActiveSignal.symbol == symbol).first()

# ==============================================================================
# ➕ سگنل شامل کریں یا پرانا اپڈیٹ کریں
# ==============================================================================
def add_or_update_active_signal(db: Session, signal_data: Dict[str, Any]) -> Optional[SignalUpdateResult]:
    try:
        symbol = signal_data.get("symbol")
        if not symbol:
            logger.error("⚠️ signal_data میں 'symbol' موجود نہیں ہے۔")
            return None

        existing = get_active_signal_by_symbol(db, symbol)
        if existing:
            for key, value in signal_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return SignalUpdateResult(signal=existing, is_new=False)
        else:
            new_signal = ActiveSignal(**signal_data)
            db.add(new_signal)
            db.commit()
            db.refresh(new_signal)
            return SignalUpdateResult(signal=new_signal, is_new=True)

    except Exception as e:
        logger.error(f"❌ سگنل شامل/اپڈیٹ کرنے میں خرابی: {e}", exc_info=True)
        return None

# ==============================================================================
# 🗑️ سگنل حذف کریں
# ==============================================================================
def delete_active_signal_by_symbol(db: Session, symbol: str):
    signal = get_active_signal_by_symbol(db, symbol)
    if signal:
        db.delete(signal)
        db.commit()

# ==============================================================================
# ✅ مکمل شدہ ٹریڈز شامل کریں
# ==============================================================================
def add_completed_trade(db: Session, trade_data: Dict[str, Any]):
    try:
        trade = CompletedTrade(**trade_data)
        db.add(trade)
        db.commit()
    except Exception as e:
        logger.error(f"❌ Completed trade save کرنے میں خرابی: {e}", exc_info=True)

# ==============================================================================
# 💬 یوزر فیڈبیک محفوظ کریں
# ==============================================================================
def save_feedback(db: Session, feedback_data: Dict[str, Any]):
    try:
        feedback = FeedbackEntry(**feedback_data)
        db.add(feedback)
        db.commit()
    except Exception as e:
        logger.error(f"❌ فیڈبیک محفوظ کرنے میں خرابی: {e}", exc_info=True)

# ==============================================================================
# 📰 نیوز کیش کریں (Cache)
# ==============================================================================
def cache_news(db: Session, news_data: Dict[str, Any]):
    try:
        news = CachedNews(**news_data)
        db.add(news)
        db.commit()
    except Exception as e:
        logger.error(f"❌ نیوز cache کرنے میں خرابی: {e}", exc_info=True)
