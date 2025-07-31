# filename: database_crud.py

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from datetime import datetime
from typing import Dict, Any, List, Optional, NamedTuple
import logging

from models import ActiveSignal, CompletedTrade, FeedbackEntry, CachedNews

logger = logging.getLogger(__name__)

class SignalUpdateResult(NamedTuple):
    signal: ActiveSignal
    is_new: bool

def get_all_active_signals_from_db(db: Session) -> List[ActiveSignal]:
    return db.query(ActiveSignal).all()

def get_active_signal_by_symbol(db: Session, symbol: str) -> Optional[ActiveSignal]:
    return db.query(ActiveSignal).filter(ActiveSignal.symbol == symbol).first()

def add_or_update_active_signal(db: Session, signal_data: Dict[str, Any]) -> Optional[SignalUpdateResult]:
    try:
        symbol = signal_data.get("symbol")
        if not symbol:
            logger.error("سگنل ڈیٹا میں 'symbol' غائب ہے۔")
            return None
        existing_signal = get_active_signal_by_symbol(db, symbol)
        if existing_signal:
            # یہ منطق اب استعمال نہیں ہونی چاہیے، لیکن حفاظتی طور پر موجود ہے
            logger.info(f"موجودہ سگنل {symbol} کو اپ ڈیٹ کیا جا رہا ہے۔")
            for key, value in signal_data.items():
                setattr(existing_signal, key, value)
            db.commit()
            db.refresh(existing_signal)
            return SignalUpdateResult(signal=existing_signal, is_new=False)
        else:
            logger.info(f"نیا سگنل {symbol} بنایا جا رہا ہے۔")
            signal_id = f"{symbol}_{signal_data.get('timeframe', '15min')}_{datetime.utcnow().timestamp()}"
            new_signal = ActiveSignal(signal_id=signal_id, **signal_data)
            db.add(new_signal)
            db.commit()
            db.refresh(new_signal)
            return SignalUpdateResult(signal=new_signal, is_new=True)
    except Exception as e:
        logger.error(f"فعال سگنل شامل/اپ ڈیٹ کرنے میں خرابی: {e}", exc_info=True)
        db.rollback()
        return None

# ★★★ یہ حتمی اور مکمل طور پر درست فنکشن ہے ★★★
def close_and_archive_signal(db: Session, signal_id: str, outcome: str, close_price: float, reason_for_closure: str) -> bool:
    """
    ایک فعال سگنل کو ڈیلیٹ کرتا ہے اور اسے مکمل شدہ ٹریڈز میں شامل کرتا ہے۔
    یہ ورژن اٹامک آپریشن کو یقینی بناتا ہے۔
    """
    try:
        # 1. سگنل کو فعال ٹیبل سے تلاش کریں
        signal_to_archive = db.query(ActiveSignal).filter(ActiveSignal.signal_id == signal_id).first()

        if signal_to_archive:
            logger.info(f"فعال سگنل {signal_id} کو بند اور آرکائیو کیا جا رہا ہے۔")

            # 2. مکمل شدہ ٹریڈ کے لیے ایک نیا آبجیکٹ بنائیں
            # (ابھی commit نہ کریں)
            completed_trade = CompletedTrade(
                signal_id=signal_to_archive.signal_id,
                symbol=signal_to_archive.symbol,
                timeframe=signal_to_archive.timeframe,
                signal_type=signal_to_archive.signal_type,
                entry_price=signal_to_archive.entry_price,
                tp_price=signal_to_archive.tp_price,
                sl_price=signal_to_archive.sl_price,
                close_price=close_price,
                reason_for_closure=reason_for_closure,
                outcome=outcome,
                confidence=signal_to_archive.confidence,
                reason=signal_to_archive.reason,
                closed_at=datetime.utcnow()
            )
            
            # 3. پہلے فعال سگنل کو ڈیلیٹ کریں
            db.delete(signal_to_archive)
            
            # 4. پھر مکمل شدہ ٹریڈ کو شامل کریں
            db.add(completed_trade)
            
            # 5. اب دونوں تبدیلیوں کو ایک ساتھ commit کریں
            db.commit()
            
            logger.info(f"سگنل {signal_id} کامیابی سے ہسٹری میں منتقل ہو گیا۔")
            return True
        else:
            # اگر سگنل فعال ٹیبل میں نہیں ملتا، تو اس کا مطلب ہے کہ یہ پہلے ہی بند ہو چکا ہے۔
            # یہ کوئی خرابی نہیں ہے، بس ایک اطلاع ہے۔
            logger.info(f"بند کرنے کے لیے فعال سگنل {signal_id} نہیں ملا۔ شاید یہ پہلے ہی بند ہو چکا ہے۔")
            return False # واپس false بھیجیں کیونکہ اس بار کوئی عمل نہیں ہوا

    except Exception as e:
        logger.error(f"فعال سگنل {signal_id} کو بند کرنے میں خرابی: {e}", exc_info=True)
        db.rollback() # کسی بھی خرابی کی صورت میں تمام تبدیلیاں واپس لے لیں
        return False

def get_completed_trades(db: Session, limit: int = 100) -> List[Dict[str, Any]]:
    trades = db.query(CompletedTrade).order_by(desc(CompletedTrade.closed_at)).limit(limit).all()
    return [trade.as_dict() for trade in trades]

def update_news_cache_in_db(db: Session, news_data: Dict[str, Any]) -> None:
    try:
        db.query(CachedNews).delete()
        new_news = CachedNews(content=news_data, updated_at=datetime.utcnow())
        db.add(new_news)
        db.commit()
    except Exception as e:
        logger.error(f"نیوز کیش اپ ڈیٹ کرنے میں خرابی: {e}", exc_info=True)
        db.rollback()

def get_cached_news(db: Session) -> Optional[Dict[str, Any]]:
    try:
        news = db.query(CachedNews).order_by(desc(CachedNews.updated_at)).first()
        return news.content if news else None
    except Exception as e:
        logger.error(f"کیش شدہ خبریں بازیافت کرنے میں خرابی: {e}", exc_info=True)
        return None

# باقی فنکشنز (get_feedback_stats_from_db, add_feedback_entry) ویسے ہی رہیں گے
def get_feedback_stats_from_db(db: Session, symbol: str) -> Dict[str, Any]:
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

def add_feedback_entry(db: Session, symbol: str, timeframe: str, feedback: str) -> Optional[FeedbackEntry]:
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
                             
