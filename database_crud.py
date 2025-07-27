# filename: database_crud.py

from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

# ★★★ ActiveSignal کو یہاں امپورٹ کریں ★★★
from models import CompletedTrade, FeedbackEntry, CachedNews, ActiveSignal

logger = logging.getLogger(__name__)

# ==============================================================================
# ★★★ فعال سگنلز کے لیے نئے فنکشنز ★★★
# ==============================================================================

def get_active_signal_by_symbol(db: Session, symbol: str) -> Optional[ActiveSignal]:
    """کسی علامت کے لیے فعال سگنل واپس کرتا ہے۔"""
    return db.query(ActiveSignal).filter(ActiveSignal.symbol == symbol).first()

def get_all_active_signals_from_db(db: Session) -> List[ActiveSignal]:
    """ڈیٹا بیس سے تمام فعال سگنلز کی فہرست واپس کرتا ہے۔"""
    return db.query(ActiveSignal).order_by(desc(ActiveSignal.created_at)).all()

def add_or_update_active_signal(db: Session, signal_data: Dict[str, Any]) -> ActiveSignal:
    """
    ایک نیا فعال سگنل شامل کرتا ہے یا اگر اسی علامت کے لیے پہلے سے موجود ہو تو اسے اپ ڈیٹ کرتا ہے۔
    """
    existing_signal = get_active_signal_by_symbol(db, signal_data['symbol'])
    
    if existing_signal:
        # سگنل کو اپ ڈیٹ کریں
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
        # نیا سگنल شامل کریں
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

# ==============================================================================
# ★★★ مکمل شدہ ٹریڈز اور فیڈ بیک کے فنکشنز ★★★
# ==============================================================================

def get_feedback_stats_from_db(db: Session, symbol: str) -> Dict[str, Any]:
    """کسی علامت کے لیے فیڈ بیک کے اعداد و شمار کا حساب لگاتا ہے۔"""
    correct_count = db.query(func.count(FeedbackEntry.id)).filter(
        FeedbackEntry.symbol == symbol, FeedbackEntry.feedback == 'correct'
    ).scalar() or 0

    incorrect_count = db.query(func.count(FeedbackEntry.id)).filter(
        FeedbackEntry.symbol == symbol, FeedbackEntry.feedback == 'incorrect'
    ).scalar() or 0

    total = correct_count + incorrect_count
    accuracy = (correct_count / total) * 100 if total > 0 else 50.0

    return {
        "total": total,
        "accuracy": round(accuracy, 2),
        "correct": correct_count,
        "incorrect": incorrect_count
    }

def add_completed_trade(db: Session, signal_data: Dict[str, Any], outcome: str) -> Optional[CompletedTrade]:
    """ڈیٹا بیس میں مکمل شدہ ٹریڈ کا ریکارڈ شامل کرتا ہے۔"""
    try:
        db_trade = CompletedTrade(
            signal_id=signal_data['signal_id'],
            symbol=signal_data['symbol'],
            timeframe=signal_data['timeframe'],
            signal_type=signal_data['signal_type'],
            entry_price=signal_data['entry_price'],
            tp_price=signal_data['tp_price'],
            sl_price=signal_data['sl_price'],
            confidence=signal_data['confidence'],
            reason=signal_data['reason'],
            outcome=outcome,
            closed_at=datetime.utcnow()
        )
        db.add(db_trade)
        return db_trade
    except Exception as e:
        logger.error(f"مکمل ٹریڈ شامل کرنے میں خرابی: {e}", exc_info=True)
        return None

# ★★★ نیا فنکشن جو دستی طور پر بند کرنے کے لیے استعمال ہوگا ★★★
def add_completed_trade_from_active(db: Session, active_signal: ActiveSignal, outcome: str) -> Optional[CompletedTrade]:
    """ایک فعال سگنل آبجیکٹ سے مکمل شدہ ٹریڈ بناتا ہے۔"""
    try:
        db_trade = CompletedTrade(
            signal_id=active_signal.signal_id,
            symbol=active_signal.symbol,
            timeframe=active_signal.timeframe,
            signal_type=active_signal.signal_type,
            entry_price=active_signal.entry_price,
            tp_price=active_signal.tp_price,
            sl_price=active_signal.sl_price,
            confidence=active_signal.confidence,
            reason=active_signal.reason,
            outcome=outcome,
            closed_at=datetime.utcnow()
        )
        db.add(db_trade)
        # یہاں کمیٹ نہیں کریں گے، تاکہ یہ ڈیلیٹ آپریشن کے ساتھ ایک ہی ٹرانزیکشن میں ہو
        return db_trade
    except Exception as e:
        logger.error(f"فعال سگنل سے مکمل ٹریڈ بنانے میں خرابی: {e}", exc_info=True)
        return None

def add_feedback_entry(db: Session, symbol: str, timeframe: str, feedback: str) -> Optional[FeedbackEntry]:
    """دی گئی علامت اور ٹائم فریم کے لیے DB میں فیڈ بیک اندراج شامل کرتا ہے۔"""
    try:
        entry = FeedbackEntry(
            symbol=symbol,
            timeframe=timeframe,
            feedback=feedback,
            created_at=datetime.utcnow()
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    except Exception as e:
        logger.error(f"فیڈ بیک اندراج شامل کرنے میں خرابی: {e}", exc_info=True)
        db.rollback()
        return None

def get_completed_trades(db: Session, limit: int = 100) -> List[Dict[str, Any]]:
    """سب سے حالیہ مکمل شدہ ٹریڈز واپس کرتا ہے۔"""
    trades = db.query(CompletedTrade).order_by(desc(CompletedTrade.closed_at)).limit(limit).all()
    return [trade.as_dict() for trade in trades]

# ==============================================================================
# ★★★ خبروں کے کیش کے فنکشنز ★★★
# ==============================================================================

def update_news_cache(db: Session, news_data: Dict[str, Any]) -> None:
    """موجودہ کیش شدہ خبروں کو نئے مواد سے بدل دیتا ہے۔"""
    try:
        db.query(CachedNews).delete()
        new_news = CachedNews(content=news_data, updated_at=datetime.utcnow())
        db.add(new_news)
        db.commit()
    except Exception as e:
        logger.error(f"نیوز کیش اپ ڈیٹ کرنے میں خرابی: {e}", exc_info=True)
        db.rollback()

def get_cached_news(db: Session) -> Optional[Dict[str, Any]]:
    """DB سے کیش شدہ خبریں حاصل کرتا ہے اگر دستیاب ہوں۔"""
    try:
        news = db.query(CachedNews).order_by(desc(CachedNews.updated_at)).first()
        return news.content if news else None
    except Exception as e:
        logger.error(f"کیش شدہ خبریں بازیافت کرنے میں خرابی: {e}", exc_info=True)
        return None
